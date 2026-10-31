import json
import pytest
from section_8_tools.web.url_policy import check_url
from section_8_tools.web.web import WebFetch


@pytest.fixture
def policy(tmp_path, monkeypatch):
    path = tmp_path / 'network_policy.json'
    monkeypatch.setenv('AI_FRIEND_URL_POLICY', str(path))
    path.write_text(json.dumps({'version': 1, 'blocked': ['bank.example', 'https://other.example/private']}))
    return path


@pytest.mark.parametrize('url', [
    'https://bank.example', 'http://login.bank.example/account',
    'https://BANK.EXAMPLE.:443/account', 'https://other.example/private/details',
    'https://other.example/a/../private', 'https://other.example/%70rivate',
])
def test_blocked_sites_and_canonical_paths(policy, url):
    with pytest.raises(PermissionError):
        check_url(url)


def test_boundary_matching_and_live_policy_reload(policy):
    check_url('https://notbank.example/')
    check_url('https://other.example/privateer')
    policy.write_text(json.dumps({'version':1, 'blocked':['notbank.example']}))
    with pytest.raises(PermissionError):
        check_url('https://notbank.example')


def test_corrupt_policy_fails_closed(policy):
    policy.write_text('broken')
    with pytest.raises(PermissionError):
        check_url('https://public.example')


def test_direct_and_redirect_fetch_never_contacts_blocked_destination(policy, tmp_path, monkeypatch):
    calls=[]
    class Redirect:
        status_code=302
        headers={'Location':'https://bank.example/account'}
        def close(self): pass
    def get(url, **kwargs):
        calls.append(url)
        assert kwargs['allow_redirects'] is False
        return Redirect()
    monkeypatch.setattr('requests.get', get)
    tool=WebFetch(tmp_path,None)
    assert not tool.call({'url':'https://bank.example'})['ok']
    assert calls==[]
    assert not tool.call({'url':'https://public.example'})['ok']
    assert calls==['https://public.example']
    with pytest.raises(PermissionError):
        tool.effects({'url':'https://bank.example'})


def test_browser_denial_applies_even_when_origin_is_explicitly_allowed(policy,tmp_path):
    from section_8_tools.web.browser import BrowserInteract
    with pytest.raises(PermissionError):
        BrowserInteract(tmp_path,None).effects({'url':'https://bank.example', 'allowed_origins':['https://bank.example']})
