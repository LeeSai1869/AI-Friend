import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'section_8_tools'))
sys.path.insert(0, str(ROOT / 'section_1_central_mind'))
from web.browser import BrowserInteract


def test_browser_declares_all_origins_before_any_interaction(tmp_path):
    tool = BrowserInteract(tmp_path, None)
    effects = tool.effects({'url': 'https://example.org/start', 'allowed_origins': ['https://cdn.example.org'],
                            'steps': [{'action': 'fill', 'selector': 'textarea', 'text': 'Question'}]})
    assert {e.target for e in effects} == {'https://example.org', 'https://cdn.example.org'}
    assert all(e.action == 'network' for e in effects)


@pytest.mark.parametrize('args', [
    {'url': 'file:///etc/passwd'}, {'url': 'https://user:secret@example.org'},
    {'url': 'https://example.org', 'steps': [{'action': 'evaluate', 'selector': 'body'}]},
    {'url': 'https://example.org', 'steps': [{'action': 'click'}]},
    {'url': 'https://example.org', 'max_chars': 100001},
    {'url': 'https://example.org', 'steps': [{'action': 'fill', 'selector': 'input', 'text': None}]},
])
def test_invalid_browser_requests_fail_before_launch(tmp_path, args):
    with pytest.raises((ValueError, TypeError)):
        BrowserInteract(tmp_path, None).effects(args)


def test_rendered_browser_interaction_and_origin_boundary(tmp_path, monkeypatch):
    import os
    if os.environ.get('AI_FRIEND_RUN_BROWSER_TESTS') != '1':
        pytest.skip('Set AI_FRIEND_RUN_BROWSER_TESTS=1 for a real Chromium check')
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from playwright.sync_api import BrowserType
    launch = BrowserType.launch
    monkeypatch.setattr(BrowserType, 'launch', lambda self, **kwargs: launch(self, executable_path='/usr/bin/chromium', **kwargs))
    class Page(BaseHTTPRequestHandler):
        def do_GET(self):
            body = b'''<html><title>Practice tutor</title><body><input id="q"><button onclick="document.querySelector('#reply').innerText='Reply: '+document.querySelector('#q').value">Ask</button><p id="reply"></p><a href="https://example.invalid/">external</a><img src="https://example.invalid/pixel"><img src="/private"></body></html>'''
            self.send_response(200); self.end_headers(); self.wfile.write(body)
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Page)
    import json
    policy = tmp_path / 'browser-policy.json'
    policy.write_text(json.dumps({'version': 1, 'blocked': [f'http://127.0.0.1:{server.server_port}/private']}))
    monkeypatch.setenv('AI_FRIEND_URL_POLICY', str(policy))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        result = BrowserInteract(tmp_path, None).call({'url': f'http://127.0.0.1:{server.server_port}',
            'steps': [{'action': 'fill', 'selector': '#q', 'text': 'Teach me'},
                      {'action': 'click', 'selector': 'button'}, {'action': 'read', 'selector': '#reply'}]})
        assert result['ok'], result
        data = result['data']
        assert 'Reply: Teach me' in data['text']
        assert data['steps_completed'] == 3 and data['memory_written'] is False
        assert data['verification'] == 'unverified_external_source'
        assert any('example.invalid' in request for request in data['blocked_requests'])
        assert any(request.endswith('/private') for request in data['blocked_requests'])
    finally:
        server.shutdown(); server.server_close(); worker.join()


def test_project_evidence_counts_nested_files_without_a_model(tmp_path):
    from section_5_domains.coding.coding_engine import CodingOrgan
    (tmp_path / 'main.py').write_text('answer = 42')
    (tmp_path / 'nested').mkdir()
    (tmp_path / 'nested' / 'readme.txt').write_text('hello')
    organ = CodingOrgan()
    organ.open_project(tmp_path)
    result = organ.handle_consultation({'consultation': {'capability': 'project_context'}})
    assert result['status'] == 'ok'
    assert result['evidence']['file_count'] == 2
    assert 'exclusions apply' in result['evidence']['file_count_scope']
