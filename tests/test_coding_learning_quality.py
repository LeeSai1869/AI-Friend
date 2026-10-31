import json
from section_5_domains.coding.learning import verified_example


def passed():
    return {'ok':True,'data':{'returncode':0,'tests_run':2,'passed':2,'failures':0,'errors':0}}


def test_syntax_only_and_failed_runs_do_not_propose_permanent_knowledge():
    common={'task':'create a.py','task_contract':{},'writes':[{'path':'a.py','content':'answer=42'}]}
    assert verified_example(**common,assessment={'ok':True},functional_result=None) is None
    assert verified_example(**common,assessment={'ok':False},functional_result=passed()) is None


def test_verified_example_preserves_contract_code_checks_and_limits():
    result=verified_example(task='Create build_index.py with --source',task_contract={'requirements':['--source']},
        writes=[{'path':'build_index.py','content':'def main():\n    pass\n'}],assessment={'ok':True},functional_result=passed())
    document=json.loads(result)
    assert document['task_contract']['requirements']==['--source']
    assert document['files'][0]['content'].startswith('def main')
    assert len(document['files'][0]['sha256'])==64
    assert document['verification']['functional_tests']['tests_run']==2
    assert document['applicability']['automatic_reuse_approved'] is False
    assert document['limitations']


def test_approved_repeat_example_keeps_one_immutable_record(tmp_path):
    from section_3_memory.api import Memory
    from section_3_memory.service import MemoryService
    memory=Memory(tmp_path);service=MemoryService(memory)
    def propose():
        return service._propose_knowledge(actor='central_mind',client_domain='Cod',domain='Cod',kind='observation',
            title='Checked example',content='Same checked source and requirements',requested_class='tested',
            source={'verified_example_fingerprint':'checked-snapshot-identity'})
    one=propose()
    first=service.commit_approved_proposal(one['proposal_id'],approved_by='central_mind',
        decision_reason='Selected behavioral tests passed',approved_class='tested')
    original=memory.store._find_path(first['memory_id']).read_bytes()
    two=propose()
    second=service.commit_approved_proposal(two['proposal_id'],approved_by='central_mind',
        decision_reason='Repeated selected behavioral tests passed',approved_class='tested')
    assert second['memory_id']==first['memory_id'] and second['reused_existing']
    assert len(list(memory.store.iter_entries()))==1
    assert memory.store._find_path(first['memory_id']).read_bytes()==original
