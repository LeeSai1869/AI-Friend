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
