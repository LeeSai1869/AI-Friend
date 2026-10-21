import json

import pytest
import yaml

from section_7_models.model_router import ModelRouter
from section_7_models.interface import build_resource_provider


def router(tmp_path, llms, assignments=None, **kwargs):
    path = tmp_path / 'registry.yaml'
    path.write_text(yaml.safe_dump({'llms': llms, 'domain_assignments': assignments or {}}))
    return ModelRouter(path, **kwargs)


def model(**kwargs):
    return {'provider': 'ollama', 'model_name': 'arbitrary:latest', 'installed': True, **kwargs}


def test_new_model_and_new_domain_need_no_kernel_changes(tmp_path):
    r = router(tmp_path, {'never-seen-before': model(eligible_domains=['another-domain'])}, availability_probe=lambda _: True)
    result = r.fulfill(requirement={'domain': 'future-domain', 'capability': 'new-capability'},
                       call_fn=lambda key, resource, messages: 'answer', messages=[])
    assert result['ok'] and result['model'] == 'never-seen-before'


def test_failed_or_invalid_json_provider_falls_back(tmp_path):
    r = router(tmp_path, {'a': model(), 'b': model()}, availability_probe=lambda _: True)
    calls = []
    def invoke(key, resource, messages):
        calls.append(key)
        return 'not json' if key == 'a' else '<think>private</think>\n```json\n{"answer":42}\n```'
    result = r.fulfill(requirement={'structured_output': 'json'}, call_fn=invoke, messages=[])
    assert calls == ['a', 'b']
    assert json.loads(result['output']) == {'answer': 42}
    assert result['attempts'] == [{'model': 'a', 'ok': False, 'error': 'JSONDecodeError'}]


def test_unavailable_models_do_not_consume_generation_budget(tmp_path):
    r = router(tmp_path, {'a': model(), 'b': model(), 'c': model(model_name='available')},
               availability_probe=lambda resource: resource['model_name'] == 'available')
    result = r.fulfill(requirement={}, call_fn=lambda *args: 'works', messages=[], max_attempts=1)
    assert result['ok'] and result['model'] == 'c'


def test_generation_failure_budget_and_no_fabricated_success(tmp_path):
    r = router(tmp_path, {str(i): model() for i in range(5)}, availability_probe=lambda _: True)
    def fail(*args):
        raise RuntimeError('do not expose credential-bearing URLs')
    result = r.fulfill(requirement={}, call_fn=fail, messages=[], max_attempts=2)
    assert not result['ok'] and len(result['attempts']) == 2
    assert 'credential' not in str(result)


def test_embedding_context_and_explicit_exclusions_remain_ineligible(tmp_path):
    r = router(tmp_path, {
        'embed': model(kind='embedding'),
        'too-small': model(context_tokens=50),
        'excluded': model(excluded_domains=['future']),
        'usable': model(context_tokens=1000),
    })
    assert [c.key for c in r._candidates({'domain': 'future', 'context_tokens': 100})] == ['usable']


def test_verified_contextual_evidence_can_reorder_bootstrap(tmp_path):
    r = router(tmp_path, {'a': model(), 'b': model()}, {'future': {'reason': {'priority': ['a']}}})
    assert r._candidates({'domain': 'future', 'capability': 'reason'})[0].key == 'a'
    assert r._candidates({'domain': 'future', 'capability': 'reason'}, {'b': 1})[0].key == 'a'
    assert r._candidates({'domain': 'future', 'capability': 'reason'}, {'b': 4})[0].key == 'b'


def test_ollama_host_is_runtime_configuration(monkeypatch):
    monkeypatch.setenv('OLLAMA_HOST', 'http://model-host:11434')
    provider = build_resource_provider(model())
    assert provider.api_url == 'http://model-host:11434'


def test_structured_requirement_reaches_real_ollama_http_payload(tmp_path, monkeypatch):
    from section_1_central_mind.mind.caller import Caller
    import requests
    payloads = []
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {'message': {'content': '{"ok":true}'}, 'done': True}
    def post(url, *, json, timeout):
        payloads.append(json)
        return Response()
    monkeypatch.setattr(requests, 'post', post)
    r = router(tmp_path, {'new-model': model()}, availability_probe=lambda _: True)
    r.registry['routing'] = {'structured_generation': {'max_tokens': 4096, 'think': False}}
    result = r.fulfill(requirement={'structured_output': 'json'},
                       call_fn=Caller(None, None)._invoke_resource, messages=[])
    assert result['ok']
    assert payloads[0]['format'] == 'json'
    assert payloads[0]['think'] is False
    assert payloads[0]['options']['num_predict'] == 4096
    assert '_generation' not in r.registry['llms']['new-model']


def test_reasoning_only_or_truncated_ollama_answer_is_diagnosed_and_falls_back(tmp_path, monkeypatch):
    from section_1_central_mind.mind.caller import Caller
    import requests
    responses = iter([
        {'message': {'content': '', 'thinking': 'private reasoning'}},
        {'message': {'content': '{"incomplete":'}, 'done_reason': 'length'},
        {'message': {'content': '{"ok":true}'}, 'done_reason': 'stop'},
    ])
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return next(responses)
    monkeypatch.setattr(requests, 'post', lambda *args, **kwargs: Response())
    r = router(tmp_path, {key: model() for key in ['a', 'b', 'c']}, availability_probe=lambda _: True)
    result = r.fulfill(requirement={'structured_output': 'json'},
                       call_fn=Caller(None, None)._invoke_resource, messages=[])
    assert result['ok'] and result['model'] == 'c'
    assert [attempt['error'] for attempt in result['attempts']] == ['reasoning_without_answer', 'output_token_limit_reached']
    assert 'private reasoning' not in str(result)


def test_unreachable_runtime_has_actionable_sanitized_failure(tmp_path, monkeypatch):
    import requests
    def fail(*args, **kwargs):
        raise requests.ConnectionError('https://user:secret@example.com/prompt')
    monkeypatch.setattr(requests, 'get', fail)
    r = router(tmp_path, {'a': model()})
    result = r.fulfill(requirement={}, call_fn=lambda *args: 'never', messages=[])
    assert not result['ok']
    assert result['attempts'][0]['error'] == 'model_service_unreachable'
    assert 'secret' not in str(result)


def test_openai_compatible_json_mode_and_truncation(monkeypatch):
    from section_7_models.providers.openai_compatible import OpenAICompatibleProvider
    import requests
    captured = []
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {'choices': [{'message': {'content': '{}'}, 'finish_reason': 'length'}]}
    def post(*args, **kwargs):
        captured.append(kwargs['json'])
        return Response()
    monkeypatch.setattr(requests, 'post', post)
    provider = OpenAICompatibleProvider('http://provider/v1', generation={'structured_output': 'json'})
    with pytest.raises(ValueError, match='output_token_limit_reached'):
        provider.chat([], model_name='arbitrary')
    assert captured[0]['response_format'] == {'type': 'json_object'}
