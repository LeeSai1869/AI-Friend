#!/usr/bin/env python3
"""Read-only logical/physical memory audit; never initialize the migrating Store."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path


def source_text(row):
    text=row.get('content','')
    context=(row.get('source') or {}).get('trainer_context')
    if isinstance(context,list) and context and all(isinstance(note,str) for note in context):
        suffix='\n\nTrainer-provided intake context (not independently verified):\n'+'\n\n'.join(context)
        if text.endswith(suffix):text=text[:-len(suffix)]
    return text


def evidence_flags(value, depth=0):
    result={}
    if not isinstance(value,dict) or depth>8:return result
    for key in ['testable','ok','functional_correctness_established']:
        if type(value.get(key)) is bool:result[key]=value[key]
    for key in ['tests_run','passed','failures','errors','returncode']:
        if type(value.get(key)) is int:result[key]=value[key]
    # Traverse evidence containers only: never emit arbitrary text or code.
    for key in ['verification','functional_tests','learning_evaluation','evidence','assessment','data']:
        if isinstance(value.get(key),dict):result.update(evidence_flags(value[key],depth+1))
    return result


def reason_category(reason):
    if not isinstance(reason,str) or not reason.strip():return 'not_recorded'
    text=reason.lower()
    for marker,label in [('no unique domain','no_unique_domain_evaluator'),('could not be loaded','evaluator_unavailable'),
                         ('no matching','no_matching_run_attestation'),('no knowledge evaluator','no_evaluator'),
                         ('not testable','untestable'),('unavailable','resource_or_verification_unavailable'),
                         ('syntax','syntax_related'),('passed','reported_pass'),('failed','reported_failure')]:
        if marker in text:return label
    return 'reason_present_not_printed'


def proposal_metadata(row):
    if not isinstance(row,dict):return {'error':'invalid_proposal_record'}
    evaluation=row.get('learning_evaluation')
    return {'proposal_id':row.get('proposal_id'),'domain':row.get('domain'),
        'status':row.get('status'),'requested_class':row.get('requested_class'),
        'approved_class':row.get('approved_class'),'memory_id':row.get('memory_id'),
        'evaluation_recorded':isinstance(evaluation,dict),
        'evaluation_flags':evidence_flags(evaluation),
        'evaluation_reason':reason_category((evaluation or {}).get('reason')) if isinstance(evaluation,dict) else 'not_recorded',
        'decision_reason':reason_category(row.get('decision_reason')),
        'submission_evidence_flags':evidence_flags(row.get('evidence'))}


def verification_metadata(row, canonical, aliases):
    source=row.get('source') if isinstance(row.get('source'),dict) else {}
    approval=source.get('memory_proposal') if isinstance(source.get('memory_proposal'),dict) else {}
    try:payload=json.loads(row.get('content',''))
    except (ValueError,TypeError):payload={}
    payload=payload if isinstance(payload,dict) else {}
    flags=evidence_flags(approval)
    flags.update(evidence_flags(payload))
    refs=row.get('source_refs') if isinstance(row.get('source_refs'),list) else []
    ambiguous={key for key in aliases if key in canonical}
    return {'id':row['id'],'domain':row.get('domain_created'),'kind':row.get('kind'),
        'content_chars':len(row['content']) if isinstance(row.get('content'),str) else None,
        'structured_kind':payload.get('kind') if payload.get('kind') in {'verified_coding_example','python_structure'} else 'other_or_legacy',
        'source_reference_count':len(refs),
        'linked_memory_reference_count':sum(isinstance(ref,str) and (ref in canonical or ref in aliases) for ref in refs),
        'ambiguous_legacy_reference_count':sum(isinstance(ref,str) and ref in ambiguous for ref in refs),
        'approval_by_mind_recorded':approval.get('approved_by')=='central_mind',
        'proposal_id':approval.get('proposal_id'), 'evidence_flags':flags,
        'success_count':row.get('success_count',0),'failure_count':row.get('failure_count',0)}


def audit(root, *, verification=False):
    root=Path(root)
    if not root.is_dir():raise ValueError(f'Memory directory not found: {root}')
    errors=[];canonical={};legacy=[];retained=[];differences=[]
    for folder in ['Raw Memory','Tested Memory','Derived Memory','entries']:
        for path in sorted((root/folder).glob('*.json')):
            if path.name.startswith('_'):continue  # sequence/index metadata is not a record
            try:
                row=json.loads(path.read_text())
                if not isinstance(row,dict) or not row.get('id'):raise ValueError('Not a memory entry')
                if folder=='entries':legacy.append(row);continue
                key=row['id']
                if key in canonical:
                    errors.append({'id':key,'reason':'ID exists in multiple canonical class folders'})
                else:canonical[key]=row
            except Exception as exc:errors.append({'file':path.name,'reason':type(exc).__name__})
    aliases={row.get('source',{}).get('legacy_id'):row['id'] for row in canonical.values()
             if row.get('memory_class')=='raw' and isinstance(row.get('source'),dict) and row['source'].get('legacy_id')}
    reused=[{'legacy_id':old,'raw_id':new,'canonical_class':canonical[old].get('memory_class')}
            for old,new in aliases.items() if old in canonical]
    for row in legacy:
        key=row['id']
        target=canonical.get(aliases.get(key)) if row.get('memory_class')=='raw' else canonical.get(key)
        if target:
            retained.append({'legacy_id':key,'canonical_id':target['id']})
            fields=[field for field in ['domain_created','memory_class','kind','content'] if row.get(field)!=target.get(field)]
            if fields:differences.append({'legacy_id':key,'canonical_id':target['id'],'differing_fields':fields})
        elif key not in canonical:canonical[key]=row
        else:errors.append({'id':key,'reason':'Unresolved legacy/canonical identity collision'})
    counts=Counter();duplicates=defaultdict(list);tested=Counter()
    for row in canonical.values():
        cls=row.get('memory_class','unknown');domain=row.get('domain_created','unknown')
        counts[f'{domain}/{cls}']+=1
        if cls=='raw':
            key=(domain,row.get('kind'),hashlib.sha256(source_text(row).encode()).hexdigest())
            duplicates[key].append(row['id'])
        if cls=='tested':
            try:payload=json.loads(row.get('content',''))
            except (ValueError,TypeError):payload={}
            tested[payload.get('kind','legacy_or_unstructured') if isinstance(payload,dict) else 'legacy_or_unstructured']+=1
    states=Counter();proposal_rows=[];proposals=root/'knowledge_proposals.json'
    if proposals.exists():
        try:
            proposal_rows=json.loads(proposals.read_text()).get('proposals',[])
            if not isinstance(proposal_rows,list):raise ValueError('Invalid proposals list')
            for row in proposal_rows:states[row.get('status','unknown')]+=1
        except Exception as exc:errors.append({'file':proposals.name,'reason':type(exc).__name__})
    if verification:
        return {'counts':dict(counts), 'tested_verification':[
            verification_metadata(row, canonical, aliases) for row in canonical.values()
            if row.get('memory_class')=='tested'],
            'proposal_reviews':[proposal_metadata(row) for row in proposal_rows],
            'reused_legacy_ids':reused,'errors':errors,'writes_performed':False,
            'interpretation':'Recorded evidence only, not an independent test or quality verdict. Missing evaluation may mean not performed OR not persisted.'}
    return {'counts':dict(counts),'tested_record_types':dict(tested),
        'exact_raw_duplicate_groups':[ids for ids in duplicates.values() if len(ids)>1],
        'retained_legacy_copies':retained,'legacy_copy_differences':differences,
        'reused_legacy_ids':reused,'proposal_statuses':dict(states),'errors':errors,'writes_performed':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('memory_root',type=Path)
    parser.add_argument('--verification',action='store_true',help='Report verification/proposal metadata without lesson contents')
    args=parser.parse_args()
    print(json.dumps(audit(args.memory_root,verification=args.verification),indent=2))
