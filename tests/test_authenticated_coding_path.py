"""Real sockets, auth, Mind, model plug and guarded Coding; deterministic model HTTP boundary.

This verifies integration, not real-model intelligence or the macOS WebView.
"""
import asyncio
import json
import shutil
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import websockets
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "section_1_central_mind"))
import bootstrap
import server
from section_1_central_mind.auth_service import AuthService
from section_3_memory.api import Memory

ROOT = Path(__file__).resolve().parents[1]


def test_authenticated_chat_mind_coding_execution(tmp_path, monkeypatch):
    prompts = []
    class ModelHTTP(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            assert self.path == '/api/tags'
            self.send_json({'models': [{'name': 'integration:latest'}]})
        def send_json(self, payload):
            body = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def do_POST(self):
            assert self.path == '/api/chat'
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            messages = body['messages']
            text = '\n'.join(m['content'] for m in messages)
            prompts.append(text)
            if 'PROPOSE a semantic' in text:
                output = json.dumps({
                    'objective_summary': 'Create answer.py returning 42',
                    'requirements': [], 'constraints': [], 'ambiguities': [],
                    'information_needs': [], 'consultations': [],
                    'candidate_steps': [{
                        'step_id': 'code', 'objective': 'Create answer.py with answer() returning 42',
                        'kind': 'domain', 'component': 'coder', 'capability': 'write_code',
                        'depends_on': [], 'requirements': [], 'constraints': [],
                        'expected_outcome': 'A Python file with the requested function',
                        'confidence': 0.95, 'rationale': ['explicit coding request'],
                    }],
                    'clarification_candidates': [], 'understanding_confidence': .95,
                    'rationale': ['explicit request'],
                })
            elif 'Answer strictly with JSON in one of these shapes' in text:
                output = json.dumps({'kind': 'code_change', 'files': ['answer.py'], 'summary': 'Create answer() returning 42'})
            else:
                output = json.dumps({'writes': [{'path': 'answer.py', 'content': 'def answer():\n    return 42\n'}]})
            self.send_json({'message': {'content': output}, 'done': True})

    model_http = ThreadingHTTPServer(('127.0.0.1', 0), ModelHTTP)
    thread = threading.Thread(target=model_http.serve_forever, daemon=True)
    thread.start()
    app_root = tmp_path / 'app'
    app_root.mkdir()
    for section in ROOT.glob('section_*'):
        if section.is_dir():
            shutil.copytree(section, app_root / section.name,
                            ignore=shutil.ignore_patterns('node_modules', 'target', '__pycache__', 'entries'))
    registry = {'llms': {'arbitrary-integration-resource': {
        'provider': 'ollama', 'model_name': 'integration:latest', 'installed': True,
        'api_url': f'http://127.0.0.1:{model_http.server_port}',
    }}}
    (app_root / 'section_7_models/models_registry.yaml').write_text(yaml.safe_dump(registry))
    isolated_memory = Memory(tmp_path / 'memory')
    monkeypatch.setattr('section_3_memory.api.Memory', lambda: isolated_memory)
    mind_instances = []
    mind_factory = server.CentralMind
    def construct_mind(**kwargs):
        mind = mind_factory(**kwargs)
        mind_instances.append(mind)
        return mind
    monkeypatch.setattr(server, "CentralMind", construct_mind)
    auth = AuthService(tmp_path / 'private/auth.sqlite3')
    auth.bootstrap_admin('test_admin', 'Integration-test-password-1')
    admin = auth.login('test_admin', 'Integration-test-password-1')
    auth.create_account(admin['token'], 'test_trainer', 'Integration-test-password-2', role='trainer')

    async def exercise():
        async def handler(ws):
            await server.handle_client(ws, app_root, auth_service=auth)
        async with websockets.serve(handler, '127.0.0.1', 0) as service:
            port = service.sockets[0].getsockname()[1]
            async with websockets.connect(f'ws://127.0.0.1:{port}') as ws:
                await ws.send(json.dumps({'op': 'login', 'username': 'test_trainer', 'password': 'Integration-test-password-2'}))
                login = json.loads(await asyncio.wait_for(ws.recv(), 10))
                assert login['op'] == 'login_result' and login['ok'], login
                await ws.send(json.dumps({'text': 'Create answer.py with answer() returning 42', 'intent': 'work'}))
                while True:
                    result = json.loads(await asyncio.wait_for(ws.recv(), 15))
                    if result.get('role') == 'mind' and result.get('chat_id'):
                        break
                assert '[mind error]' not in result['text'], result
                assert 'syntax check succeeded' in result['text'], result
                assert (app_root / 'answer.py').read_text() == 'def answer():\n    return 42\n'
                assert result['chat_id']
                history = app_root / '.central_mind/chats' / result['chat_id'] / 'turns.json'
                assert 'syntax check succeeded' in history.read_text()
                # Shared model routing is used by both semantic reasoning and Coding.
                assert any('PROPOSE a semantic' in prompt for prompt in prompts)
                assert any('Write the change' in prompt for prompt in prompts)
                # Learning stays proposal-based, and system activity creates no Raw entry.
                assert all(entry.memory_class != 'raw' for entry in isolated_memory.store.iter_entries())
                mind = mind_instances[-1]
                journal = json.loads((tmp_path / 'memory/knowledge_proposals.json').read_text())
                proposal = journal['proposals'][-1]
                assert proposal['status'] == 'approved'
                assert proposal['requested_class'] == 'derived'
                evaluated = mind._receive_memory_proposal(proposal)
                assert evaluated['learning_evaluation']['ok'], evaluated
                assert evaluated['learning_evaluation']['evidence']['functional_correctness_established'] is False
                recalled = mind.memory.recall_tested(query='answer', domain='Cod', limit=5)
                assert recalled and 'functional correctness is unverified' in recalled[0]['content']
    try:
        asyncio.run(exercise())
    finally:
        model_http.shutdown()
        model_http.server_close()
        thread.join(timeout=5)
