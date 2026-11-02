#!/usr/bin/env python3
"""Read-only turn/provider trace; never print recalled lessons or model prose."""
import argparse
from collections import deque
import json
from pathlib import Path


def records(path):
    if not path.exists():return []
    rows=deque(maxlen=256)
    with path.open() as handle:
        for line in handle:
            try:row=json.loads(line)
            except (ValueError,TypeError):continue  # an in-flight append can be incomplete
            if isinstance(row,dict):rows.append(row)
    return list(rows)


def steps(rows):
    return [{key:row.get(key) for key in ['step_id','kind','component','capability']}
            for row in rows if isinstance(row,dict)] if isinstance(rows,list) else []


def trace(root):
    root=Path(root)/'debug'
    turns=records(root/'chat_turns.jsonl')
    turn=turns[-1] if turns else {}
    plan={};plan_state='not_recorded'
    if turn.get('plan'):
        try:
            plan=json.loads(turn['plan']);plan_state='parsed'
        except (ValueError,TypeError):plan_state='legacy_plan_truncated_or_invalid'
    semantic=[];recent=[]
    for row in records(root/'model_calls.jsonl'):
        recent.append({key:row.get(key) for key in ['ts','domain','capability','model','elapsed_s','ok','attempts']})
        if row.get('domain')!='general' or row.get('capability')!='reason':continue
        try:proposal=json.loads(row.get('output') or '')
        except (ValueError,TypeError):continue
        if isinstance(proposal,dict) and 'candidate_steps' in proposal:
            semantic.append({'ts':row.get('ts'),'model':row.get('model'),
                             'candidate_steps':steps(proposal.get('candidate_steps')),
                             'information_need_count':len(proposal.get('information_needs') or [])})
    return {'latest_completed_turn':{key:turn.get(key) for key in ['ts','status','disposition','reasoning_dropped_steps']},
            'plan_diagnostic':plan_state,'plan_steps':steps(turn.get('reasoning_steps') or plan.get('steps')),
            'execution_summary':turn.get('execution_summary'),
            'recent_semantic_proposals':semantic[-3:],'recent_model_calls':recent[-8:],
            'note':'Recent proposals may be from different turns; compare timestamps. Truncated legacy model outputs cannot be reconstructed. This report omits model prose, memory contents and source files.',
            'writes_performed':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-root',type=Path,default=Path.home()/'Library/Application Support/AI Friend V1 Dev/state')
    print(json.dumps(trace(parser.parse_args().state_root),indent=2))
