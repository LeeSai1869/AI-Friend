#!/usr/bin/env python3
"""Read JSON records directly: no Store initialization, migration or writes."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path


def audit(root):
    root=Path(root)
    if not root.is_dir():raise ValueError(f'Memory directory not found: {root}')
    counts=Counter();duplicates=defaultdict(list);tested=Counter();errors=[];seen={}
    for folder in ['Raw Memory','Tested Memory','Derived Memory','entries']:
        for path in sorted((root/folder).glob('*.json')):
            try:
                row=json.loads(path.read_text())
                if not isinstance(row,dict) or not row.get('id'):raise ValueError('Not a memory entry')
                record_id=row['id']
                digest=hashlib.sha256(path.read_bytes()).hexdigest()
                if record_id in seen:
                    if seen[record_id]!=digest:errors.append({'id':record_id,'reason':'Conflicting physical copies'})
                    continue
                seen[record_id]=digest
                cls=row.get('memory_class','unknown');domain=row.get('domain_created','unknown')
                counts[f'{domain}/{cls}']+=1
                if cls=='raw':
                    text=row.get('content','')
                    context=(row.get('source') or {}).get('trainer_context')
                    if isinstance(context,list) and context and all(isinstance(note,str) for note in context):
                        suffix='\n\nTrainer-provided intake context (not independently verified):\n'+'\n\n'.join(context)
                        if text.endswith(suffix):text=text[:-len(suffix)]
                    key=(domain,row.get('kind'),hashlib.sha256(text.encode()).hexdigest())
                    duplicates[key].append(record_id)
                if cls=='tested':
                    try:payload=json.loads(row.get('content',''))
                    except (ValueError,TypeError):payload={}
                    tested[payload.get('kind','legacy_or_unstructured') if isinstance(payload,dict) else 'legacy_or_unstructured']+=1
            except Exception as exc:errors.append({'file':path.name,'reason':type(exc).__name__})
    proposals=root/'knowledge_proposals.json'
    states=Counter()
    if proposals.exists():
        try:
            for row in json.loads(proposals.read_text()).get('proposals',[]):states[row.get('status','unknown')]+=1
        except Exception as exc:errors.append({'file':proposals.name,'reason':type(exc).__name__})
    return {'counts':dict(counts),'tested_record_types':dict(tested),
        'exact_raw_duplicate_groups':[ids for ids in duplicates.values() if len(ids)>1],
        'proposal_statuses':dict(states),'errors':errors,'writes_performed':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('memory_root',type=Path)
    args=parser.parse_args()
    print(json.dumps(audit(args.memory_root),indent=2))
