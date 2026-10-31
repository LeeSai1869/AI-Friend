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


def audit(root):
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
    states=Counter();proposals=root/'knowledge_proposals.json'
    if proposals.exists():
        try:
            for row in json.loads(proposals.read_text()).get('proposals',[]):states[row.get('status','unknown')]+=1
        except Exception as exc:errors.append({'file':proposals.name,'reason':type(exc).__name__})
    return {'counts':dict(counts),'tested_record_types':dict(tested),
        'exact_raw_duplicate_groups':[ids for ids in duplicates.values() if len(ids)>1],
        'retained_legacy_copies':retained,'legacy_copy_differences':differences,
        'reused_legacy_ids':reused,'proposal_statuses':dict(states),'errors':errors,'writes_performed':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('memory_root',type=Path)
    print(json.dumps(audit(parser.parse_args().memory_root),indent=2))
