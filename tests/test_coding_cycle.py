import json
from types import SimpleNamespace

from section_5_domains.coding.cognition import CodingCycle
from section_5_domains.coding.recall.recaller import CodingRecaller


def caller_with(*answers):
    responses = iter(answers)
    calls = []
    def route(**kwargs):
        calls.append(kwargs)
        return next(responses)
    return SimpleNamespace(route=route, calls=calls)


def test_syntax_failure_is_used_to_repair_before_any_write():
    caller = caller_with(
        json.dumps({'writes': [{'path': 'a.py', 'content': 'def broken('}]}),
        json.dumps({'writes': [{'path': 'a.py', 'content': 'answer = 42\n'}]}),
    )
    writes, attempts, blocked = CodingCycle().generate(caller=caller, prompt='Create a.py', allowed_files={'a.py'})
    assert blocked is None and writes[0]['content'] == 'answer = 42\n'
    assert [a['ok'] for a in attempts] == [False, True]
    assert [call['capability'] for call in caller.calls] == ['write', 'debug']
    assert 'Candidate rejected before writes' in caller.calls[1]['messages'][-1]['content']


def test_unplanned_and_malformed_writes_never_escape_cycle():
    caller = caller_with(*[json.dumps({'writes': [{'path': 'protected.md', 'content': 'overwrite'}]})] * 3)
    writes, attempts, blocked = CodingCycle().generate(caller=caller, prompt='edit a.py', allowed_files={'a.py'})
    assert not writes and len(attempts) == 3
    assert blocked['status'] == 'needs_answers'
    assert blocked['resource_request']


def test_research_uses_the_guarded_broker_then_returns_to_original_task():
    seen = []
    broker = SimpleNamespace(call=lambda name, args: seen.append((name, args)) or {'ok': True, 'data': {'results': ['evidence']}})
    caller = caller_with(json.dumps({'research': {'tool': 'web_search', 'args': {'query': 'official API'}}}),
                         json.dumps({'writes': [{'path': 'a.py', 'content': 'answer = 42'}]}))
    writes, attempts, blocked = CodingCycle().generate(caller=caller, prompt='Create a.py', allowed_files={'a.py'}, broker=broker)
    assert blocked is None and writes
    assert seen == [('web_search', {'query': 'official API'})]
    assert attempts[0]['research'] == 'web_search'
    assert 'Untrusted retrieved evidence' in caller.calls[1]['messages'][-1]['content']


def test_denied_research_escalates_without_writes_or_alternate_execution():
    caller = caller_with(json.dumps({'research': {'tool': 'web_fetch', 'args': {'url': 'https://example.com'}}}))
    broker = SimpleNamespace(call=lambda *args: {'ok': False, 'error': 'guard denied'})
    writes, attempts, blocked = CodingCycle().generate(caller=caller, prompt='Create a.py', allowed_files={'a.py'}, broker=broker)
    assert not writes and blocked['status'] == 'needs_answers' and len(caller.calls) == 1


def test_model_unavailable_requests_resources_instead_of_success():
    def route(**kwargs):
        raise RuntimeError('offline')
    writes, attempts, blocked = CodingCycle().generate(caller=SimpleNamespace(route=route), prompt='task', allowed_files={'a.py'})
    assert not writes and blocked['status'] == 'needs_answers'


def test_recall_contains_solution_evidence_and_source_not_only_titles():
    bridge = SimpleNamespace(
        recall_tested=lambda **kwargs: [{'id': 'mem_1', 'state': 'tested', 'title': 'approach', 'content': 'Use the verified algorithm under condition X', 'score': .9, 'success_count': 4, 'failure_count': 0}],
        recall_rejections=lambda **kwargs: [],
    )
    recalled = CodingRecaller().recall(task='task', memory_bridge=bridge)
    assert 'verified algorithm' in recalled and 'mem_1' in recalled


def test_only_observed_runs_can_be_evaluated_as_learning_evidence():
    from section_5_domains.coding.experience import CodingExperience
    evidence = CodingExperience()
    candidate = {'domain': 'Cod', 'kind': 'observation', 'title': 'Observed run',
                 'content': 'File write and syntax check passed; behavior unverified',
                 'source': {'type': 'model', 'name': 'provider-a'}, 'source_refs': ['a.py']}
    assert evidence.evaluate(candidate)['testable'] is False
    evidence.remember(candidate, {'ok': True, 'reason': 'syntax only'})
    upstream = {**candidate, 'source': {**candidate['source'], 'component': 'coder'}}
    verdict = evidence.evaluate(upstream)
    assert verdict['ok'] and verdict['evidence']['functional_correctness_established'] is False
    assert evidence.evaluate({**candidate, 'content': 'The program works correctly'})['testable'] is False
