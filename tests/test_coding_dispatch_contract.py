from types import SimpleNamespace
from section_5_domains.coding.coding_engine import CodingOrgan


def dispatch(*responses):
    organ = CodingOrgan()
    calls = []
    answers = iter(responses)
    def classify(**kwargs):
        calls.append(kwargs['task'])
        return next(answers)
    organ.classifier = SimpleNamespace(classify=classify)
    organ.recaller = SimpleNamespace(recall=lambda **kwargs: '')
    organ.operations = SimpleNamespace(plan=lambda **kwargs: (_ for _ in ()).throw(AssertionError('must not plan')))
    result = organ.handle({'text': 'Create build_index.py using --source',
                           'broker': object(), 'caller': object(),
                           'cognitive_plan': {'selected_capability': 'write_code'}})
    return result, calls


def test_repeated_plan_cannot_succeed_as_delegated_write():
    result, calls = dispatch({'kind': 'plan'}, {'kind': 'plan'})
    assert result['status'] == 'error' and result['artifacts'] == []
    assert 'No files were written' in result['error']
    assert len(calls) == 2 and '--source' in calls[1]


def test_material_clarification_remains_allowed_after_dispatch_repair():
    result, calls = dispatch({'kind': 'plan'}, {'kind': 'clarify', 'questions': ['Which output format?']})
    assert result['status'] == 'needs_answers'
    assert result['questions'][0]['question'] == 'Which output format?'


def test_existing_clarification_is_not_forced_into_a_write():
    result, calls = dispatch({'kind': 'clarify', 'questions': ['Which output format?']})
    assert result['status'] == 'needs_answers' and len(calls) == 1


def test_single_step_cannot_expand_to_later_global_file_targets():
    organ=CodingOrgan()
    classifications=iter([
        {'kind':'code_change','files':['add_values.py','test_add_values.py']},
        {'kind':'code_change','files':['add_values.py']},
    ])
    tasks=[];reads=[]
    def classify(**kwargs):
        tasks.append(kwargs['task'])
        return next(classifications)
    organ.classifier=SimpleNamespace(classify=classify)
    organ.recaller=SimpleNamespace(recall=lambda **kwargs:'')
    broker=SimpleNamespace(call=lambda name,args: reads.append(args['path']) or {'ok':False,'error':'guard denied'})
    response=organ.handle({'text':'Original objective: create add_values.py and test_add_values.py',
        'broker':broker,'caller':object(),'cognitive_plan':{
            'steps':[{'kind':'domain','component':'coder','capability':'write_code','objective':'Create add_values.py with add(a: int, b: int) -> int.'}],
            'requirements':['Later create test_add_values.py and run the tests.']}})
    assert len(tasks)==2 and 'Scope correction' in tasks[1]
    assert 'Later create test_add_values.py' in tasks[0]  # global requirements were not discarded
    assert reads==['add_values.py'] and response['status']=='error'


def test_repeated_scope_violation_is_rejected_before_file_access():
    organ=CodingOrgan()
    organ.classifier=SimpleNamespace(classify=lambda **kwargs:{'kind':'code_change','files':['later.py']})
    organ.recaller=SimpleNamespace(recall=lambda **kwargs:'')
    result=organ.handle({'text':'Create first.py then later.py','broker':object(),'caller':object(),
        'cognitive_plan':{'steps':[{'kind':'domain','component':'coder','capability':'write_code','objective':'Create first.py'}]}})
    assert result['status']=='error' and result['artifacts']==[]
    assert 'scope' in result['error']


def test_current_step_can_explicitly_request_conventional_tests_but_global_context_cannot():
    from section_5_domains.coding.conventions import delegated_write_scope
    def scope(objective):
        return delegated_write_scope({'steps':[{'kind':'domain','objective':objective}],
                                      'requirements':['Create tests for every file']})
    assert scope('Create package/add.py and add tests')==['package/add.py','package/test_add.py']
    assert scope('Create package/add.py then run tests')==['package/add.py']
