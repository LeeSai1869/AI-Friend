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
