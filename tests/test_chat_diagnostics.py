import json
from types import SimpleNamespace
from section_4_chatbox.runtime import ChatRuntime


def test_diagnostic_preserves_dispatch_and_counts_without_raw_or_code(tmp_path):
    runtime=ChatRuntime.__new__(ChatRuntime)
    runtime.workspace=tmp_path
    runtime.mind=SimpleNamespace(reasoner=SimpleNamespace(last_evidence=[],last_dropped_steps=[]))
    step={'step_id':'execute','kind':'domain','component':'coder','capability':'test_code','objective':'Run existing tests'}
    result={'status':'ok','cognition':{'plan':{'objective':'Run tests','steps':[step],
        'recalled_memory':[{'id':'raw_guide_abcdefgh','memory_class':'raw','content':'PRIVATE RAW '*10000,
                            'source':{'files':['PRIVATE FILE']*1000},'content_chars':120000}]}},
        'outcome':{'execution':{'status':'completed'},'verification':{'status':'passed'},'receipts':[
            {'component':'coder','capability':'test_code','status':'ok','operation':'test_run',
             'functional_tests':{'ok':True,'data':{'tests_run':2,'passed':2,'failures':0,'errors':0,'output':'PRIVATE OUTPUT'}}}]}}
    runtime._debug_turn('Run tests',result)
    text=(tmp_path/'debug/chat_turns.jsonl').read_text()
    row=json.loads(text)
    assert json.loads(row['plan'])['steps'][0]['capability']=='test_code'
    assert row['reasoning_steps'][0]['capability']=='test_code'
    assert row['execution_summary']['receipts'][0]['tests']['passed']==2
    assert 'PRIVATE' not in text
    assert len(text)<5000
