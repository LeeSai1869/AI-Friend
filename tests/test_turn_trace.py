import json
from scripts.turn_trace import trace


def test_trace_recovers_semantic_steps_without_printing_legacy_raw_context(tmp_path):
    debug=tmp_path/'debug';debug.mkdir()
    (debug/'chat_turns.jsonl').write_text(json.dumps({'ts':20,'status':'ok','plan':'{"recalled_memory":"PRIVATE RAW CUT OFF'})+'\n')
    proposal={'candidate_steps':[{'step_id':'say','kind':'communicate','component':None,'capability':None,'objective':'PRIVATE OBJECTIVE'}],
              'objective_summary':'PRIVATE TEXT','information_needs':[]}
    (debug/'model_calls.jsonl').write_text(json.dumps({'ts':19,'domain':'general','capability':'reason','model':'fixture','output':json.dumps(proposal)})+'\n'+'incomplete append')
    report=trace(tmp_path)
    assert report['plan_diagnostic']=='legacy_plan_truncated_or_invalid'
    assert report['recent_semantic_proposals'][0]['candidate_steps'][0]['kind']=='communicate'
    assert 'PRIVATE' not in json.dumps(report) and report['writes_performed'] is False
