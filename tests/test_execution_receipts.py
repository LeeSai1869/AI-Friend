import json
from types import SimpleNamespace
from section_1_central_mind.mind.cognition import CognitivePlan, CognitiveStep
from section_1_central_mind.mind.task_contract import task_contract
from section_4_chatbox.runtime import ChatRuntime
from tests.test_chat_render_review import _mind, _step


def test_failed_explanation_preserves_durable_receipts_and_retry_never_calls_a_domain(tmp_path):
    mind = _mind('{"approved":false,"issues":["Unsupported detail"]}')
    plan = CognitivePlan(objective='Create answer.py', requirements=['Return 42'])
    result = {'status':'ok','artifacts':['answer.py'], 'execution_receipts':[{
        'component':'coder', 'status':'ok', 'artifacts':['answer.py'],
        'verification':{'checks':{'python_syntax':'passed'}}, 'functional_tests':None,
    }]}
    response = mind._communicate(plan, _step(), ['file writes completed'], [], {'code':result})
    assert response['status'] == 'error'
    assert response['artifacts'] == ['answer.py']
    assert 'File written: answer.py' in response['output']
    assert 'Unsupported detail' not in response['output']
    assert response['outcome']['execution']['status'] == 'completed'
    assert response['outcome']['verification']['status'] == 'insufficient'
    assert response['outcome']['communication']['retry_available']
    mind.process = lambda *args, **kwargs: response
    runtime = ChatRuntime(mind, tmp_path, owner='trainer')
    delivered = runtime.respond('Create answer.py')
    restored = ChatRuntime(mind, tmp_path, owner='trainer').load_chat(delivered['chat_id'])
    assert restored['turns'][-1]['outcome'] == response['outcome']
    before = len(mind.resource_socket.requests)
    mind.resource_socket.review = '{"approved":true,"issues":[]}'
    retried = runtime.retry_reply(delivered['chat_id'], response['task_id'])
    assert retried['status'] == 'ok'
    assert retried['outcome']['execution']['artifacts'] == ['answer.py']
    assert all(requirement.kind == 'model' for requirement, _ in mind.resource_socket.requests[before:])
    assert ChatRuntime(mind, tmp_path, owner='other').retry_reply(delivered['chat_id'], response['task_id'])['status'] == 'error'


def test_delegation_keeps_original_request_and_all_global_constraints():
    from tests.test_loop_verification import make_mind, StubOrgan
    organ = StubOrgan({'status':'ok','output':'Complete','artifacts':[]}, {'ok':True})
    mind = make_mind(organ)
    plan = CognitivePlan(objective='Count every entry including duplicates',
        requirements=['Return the number of entries'], constraints=['Never deduplicate'],
        steps=[CognitiveStep(step_id='write', objective='Implement counter.py', component=organ.name, capability='perform',
                             requirements=['Use count_entries'])])
    mind.process(plan.objective, plan=plan)
    request = organ.requests[-1]
    assert 'including duplicates' in request['text']
    assert request['cognitive_plan']['constraints'] == ['Never deduplicate']
    assert request['cognitive_plan']['requirements'] == ['Return the number of entries', 'Use count_entries']
    assert request['task_contract']['original_objective'] == plan.objective
    assert [row['id'] for row in request['task_contract']['requirements']] == ['R1','R2']


def test_malformed_task_contract_is_rejected_before_tools_or_models_are_called():
    from section_5_domains.coding.coding_engine import CodingOrgan
    domain=CodingOrgan()
    response=domain.handle({'text':'Write a file','task_contract':{'schema_version':999}})
    assert response['status']=='error' and response['artifacts']==[]
    assert 'contract version' in response['error']


def test_partial_write_failure_keeps_confirmed_artifacts_without_claiming_completion():
    from section_1_central_mind.mind.task_contract import attach_outcome, execution_receipt
    plan=CognitivePlan(objective='Write two files')
    task_contract(plan)
    receipt=execution_receipt({'status':'error','applied':[
        {'path':'a.py','ok':True},{'path':'b.py','ok':False,'error':'denied'}]},
        {'ok':False},component='worker',capability='perform')
    response=attach_outcome({'status':'error','error':'partial application'},plan,
        {'write':{'execution_receipts':[receipt]}},communication='not_attempted')
    assert response['artifacts']==['a.py']
    assert response['outcome']['execution']['status']=='partial'
    assert response['outcome']['verification']['status']=='failed'
    assert 'File written: a.py' in response['output'] and 'File written: b.py' not in response['output']


def test_clarification_answer_does_not_replace_the_original_task_contract(tmp_path):
    from tests.test_loop_verification import make_mind, StubOrgan
    organ=StubOrgan({'status':'ok','output':'Complete','artifacts':[]},{'ok':True})
    mind=make_mind(organ)
    def plan(text, **kwargs):
        if text=='Create counter.py using the format I want':
            return CognitivePlan(objective=text,should_clarify=True,
                clarification_questions=[{'attribute':'format','question':'Which format?'}])
        return CognitivePlan(objective=text,steps=[CognitiveStep(step_id='write',objective='Create counter.py with JSON output',
            component=organ.name,capability='perform')])
    mind.reasoner.plan=plan
    runtime=ChatRuntime(mind,tmp_path,owner='trainer')
    first=runtime.respond('Create counter.py using the format I want')
    assert first['status']=='needs_answers'
    second=runtime.respond('JSON',chat_id=first['chat_id'])
    assert second['status']=='ok'
    contract=organ.requests[-1]['task_contract']
    assert contract['original_objective']=='Create counter.py using the format I want'
    assert 'JSON' in organ.requests[-1]['text']
