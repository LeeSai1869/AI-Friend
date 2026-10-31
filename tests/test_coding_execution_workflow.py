import json
from pathlib import Path
from types import SimpleNamespace

from section_5_domains.coding.execution import CodingExecution
from section_5_domains.coding.coding_engine import CodingOrgan


def result(ok):
    return {'ok': ok, 'data': {'returncode': 0 if ok else 1, 'tests_run': 1,
            'passed': 1 if ok else 0, 'failures': 0 if ok else 1, 'errors': 0,
            'output': 'expected 42'}, 'error': None if ok else 'assertion failed'}


def test_functional_failure_repairs_before_application_and_retests_actual_writes():
    calls, prompts = [], []
    content = iter(['def answer():\n    return 41\n', 'def answer():\n    return 42\n'])
    def route(**kwargs):
        prompts.append(kwargs)
        return json.dumps({'writes': [{'path': 'answer.py', 'content': next(content)}]})
    def call(name, args):
        calls.append((name, args))
        if name == 'run_python_tests':
            return result(not args['overrides'] or '42' in args['overrides']['answer.py'])
        return {'ok': True, 'data': {'returncode': 0}}
    execution = CodingExecution().run(caller=SimpleNamespace(route=route), broker=SimpleNamespace(call=call),
        prompt='Repair answer.py', allowed_files=['answer.py'], tests=['test_answer.py'], sources=['answer.py','test_answer.py'])
    assert execution['status'] == 'executed'
    assert [name for name, _ in calls] == ['run_python_tests','run_python_tests','write_file','run_python_compile','run_python_tests']
    assert '42' in next(args['content'] for name, args in calls if name == 'write_file')
    assert prompts[1]['capability'] == 'debug'
    assert 'expected 42' in prompts[1]['messages'][0]['content']


def test_failed_candidates_exhaust_budget_without_host_writes():
    calls = []
    def call(name, args):
        calls.append(name)
        return result(False)
    caller = SimpleNamespace(route=lambda **kwargs: json.dumps({'writes':[{'path':'answer.py','content':'value = 41'}]}))
    execution = CodingExecution().run(caller=caller, broker=SimpleNamespace(call=call), prompt='task',
        allowed_files=['answer.py'], tests=['test_answer.py'], sources=['answer.py','test_answer.py'])
    assert execution['status'] == 'error' and execution['artifacts'] == []
    assert calls == ['run_python_tests'] * 3


def test_test_runtime_unavailable_asks_for_resources_without_writes():
    calls = []
    def call(name, args):
        calls.append(name)
        return {'ok':False,'data':None,'error':'Docker unavailable'}
    caller = SimpleNamespace(route=lambda **kwargs: json.dumps({'writes':[{'path':'answer.py','content':'value = 42'}]}))
    execution = CodingExecution().run(caller=caller, broker=SimpleNamespace(call=call), prompt='task',
        allowed_files=['answer.py'], tests=['test_answer.py'], sources=['answer.py','test_answer.py'])
    assert execution['status'] == 'needs_answers' and calls == ['run_python_tests']


def test_denied_application_stops_and_reports_partial_writes():
    calls = []
    def call(name, args):
        calls.append((name,args))
        return {'ok':args['path']=='a.py','data':None,'error':'denied'}
    caller=SimpleNamespace(route=lambda **kwargs:json.dumps({'writes':[
        {'path':'a.py','content':'a=1'}, {'path':'b.py','content':'b=2'}, {'path':'c.py','content':'c=3'}]}))
    execution=CodingExecution().run(caller=caller,broker=SimpleNamespace(call=call),prompt='task',allowed_files=['a.py','b.py','c.py'])
    assert execution['status']=='error' and execution['artifacts']==['a.py']
    assert [args['path'] for _,args in calls]==['a.py','b.py']


def test_project_context_is_isolated_per_trusted_caller(tmp_path):
    one, two = tmp_path/'one', tmp_path/'two'
    one.mkdir(); two.mkdir()
    class Caller:
        pass
    first, second = Caller(), Caller()
    domain = CodingOrgan(session_scoped=False)
    for caller, root in [(first, one), (second, two)]:
        response = domain.handle_application({'caller':caller,'operation':'open_project','payload':{'root':str(root)}})
        assert response['status']=='ok'
    assert domain.handle_application({'caller':first,'operation':'project_status'})['result']['project']['root']==str(one)
    assert domain.handle_application({'caller':second,'operation':'project_status'})['result']['project']['root']==str(two)


def test_trusted_planning_capability_cannot_be_reclassified_as_a_write(tmp_path):
    domain=CodingOrgan()
    domain.open_project(tmp_path)
    domain.operations.plan=lambda **kwargs:{'status':'ok','operation':'no_change','output':'Plan','artifacts':[]}
    domain.classifier.classify=lambda **kwargs: (_ for _ in ()).throw(AssertionError('must not classify planning as mutation'))
    class Broker:
        def with_workspace(self, root):
            return self
    result=domain.handle({'text':'Plan implementation','caller':object(),'broker':Broker(),
        'cognitive_plan':{'steps':[{'kind':'domain','component':'coder','capability':'plan_code'}]}})
    assert result['status']=='ok' and result['artifacts']==[]


def test_new_test_file_is_included_in_candidate_execution_before_any_write():
    domain=CodingOrgan()
    domain.classifier=SimpleNamespace(classify=lambda **kwargs:{'kind':'code_change',
        'files':['add.py','test_add.py'],'summary':'Create implementation and tests'})
    domain.recaller=SimpleNamespace(recall=lambda **kwargs:'')
    observed={};calls=[]
    def execute(**kwargs):
        observed.update(kwargs)
        return {'status':'needs_answers','artifacts':[],'error':'test runtime probe'}
    domain.execution=SimpleNamespace(run=execute)
    def call(name,args):
        calls.append(name)
        return {'ok':False,'error':'not found: '+args['path']}
    result=domain.handle({'text':'Create add.py and test_add.py with tests',
                         'broker':SimpleNamespace(call=call),'caller':object(),
                         'cognitive_plan':{'selected_capability':'write_code'}})
    assert observed['tests']==['test_add.py']
    assert set(observed['allowed_files'])=={'add.py','test_add.py'}
    assert 'write_file' not in calls and result['status']=='needs_answers'
