"""Browser UI -> real Chat/Mind/Coding/Guard -> real isolated tests -> browser UI.

Only model responses and the native Tauri window/dialog bridge are controlled
fixtures. Auth, sockets, persistence, domain discovery, tool execution and UI
modules are the production implementations.
"""
import asyncio
from functools import partial
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import sys
import threading

import pytest
import websockets
import yaml

from section_1_central_mind.auth_service import AuthService
from section_3_memory.api import Memory
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "section_1_central_mind"))
import bootstrap
import server

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def browser_stack(tmp_path, monkeypatch):
    if os.environ.get('AI_FRIEND_RUN_BROWSER_TESTS') != '1':
        pytest.skip('enable AI_FRIEND_RUN_BROWSER_TESTS=1 for the browser/native-container integration')
    pytest.importorskip('playwright.sync_api')
    assert os.environ.get('AI_FRIEND_TEST_IMAGE'), 'configure the reviewed functional test image'
    project = tmp_path / 'project'
    project.mkdir()
    (project / 'answer.py').write_text('def answer():\n    return 0\n')
    (project / 'test_answer.py').write_text(
        'import unittest\nfrom answer import answer\nclass AnswerTests(unittest.TestCase):\n'
        '    def test_answer(self):\n        self.assertEqual(answer(), 42)\n')
    events = {'repair_saw_original': False, 'communication_evidence': [], 'minds': [], 'prompts': []}

    class ModelHTTP(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def send_json(self, data):
            body = json.dumps(data).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def do_GET(self):
            self.send_json({'models': [{'name': 'fixture-resource:latest'}]})
        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            text = '\n'.join(message['content'] for message in request['messages'])
            events['prompts'].append(text)
            if 'PROPOSE a semantic' in text:
                payload = json.loads(request['messages'][-1]['content'])
                objective = payload['objective']
                pending = payload['supplied_context'].get('pending_clarification')
                needs_answer = '42' not in objective and not objective.lower().startswith('hello')
                greeting = objective.lower().startswith('hello')
                steps = [] if needs_answer else ([{
                    'step_id': 'say', 'objective': 'Greet the user', 'kind': 'communicate',
                    'component': None, 'capability': None, 'depends_on': [], 'confidence': .95,
                }] if greeting else [
                    {'step_id': 'implement', 'objective': 'Fix answer.py so answer() returns 42',
                     'kind': 'domain', 'component': 'coder', 'capability': 'write_code',
                     'depends_on': [], 'confidence': .95},
                    {'step_id': 'explain', 'objective': 'Explain the verified outcome and changed files',
                     'kind': 'communicate', 'component': None, 'capability': None,
                     'depends_on': ['implement'], 'confidence': .95},
                ])
                if objective.strip() == '42':
                    assert pending and 'answer.py' in pending['objective']
                output = json.dumps({
                    'objective_summary': objective, 'requirements': [], 'constraints': [],
                    'ambiguities': ['required return value'] if needs_answer else [],
                    'information_needs': [{'subject': 'required return value', 'reason': 'not supplied', 'material': True}] if needs_answer else [],
                    'consultations': [], 'candidate_steps': steps,
                    'clarification_candidates': [{'attribute': 'required return value', 'question': 'What value should answer() return?',
                                                  'options': [], 'default': None}] if needs_answer else [],
                    'understanding_confidence': .4 if needs_answer else .95,
                    'rationale': ['the task depends on the requested value' if needs_answer else 'sufficient context'],
                })
            elif "Render Central Mind's final response" in text:
                payload = json.loads(request['messages'][-1]['content'])
                events['communication_evidence'].append(payload['verified_evidence'])
                output = ('Implemented answer.py and verified the selected behavior.\n' + '\n'.join(payload['verified_evidence'])
                          if payload['verified_evidence'] else 'Hello. How can I help?')
            elif 'Answer strictly with JSON in one of these shapes' in text:
                output = json.dumps({'kind': 'code_change', 'files': ['answer.py'], 'tests': ['test_answer.py'],
                                     'summary': 'Return the requested value'})
            else:
                repair = 'Functional test failure evidence' in text
                if repair:
                    events['repair_saw_original'] = (project / 'answer.py').read_text().endswith('return 0\n')
                output = json.dumps({'writes': [{'path': 'answer.py', 'content': f'def answer():\n    return {42 if repair else 41}\n'}]})
            self.send_json({'message': {'content': output}, 'done': True})

    class StaticHTTP(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    model_http = ThreadingHTTPServer(('127.0.0.1', 0), ModelHTTP)
    static_http = ThreadingHTTPServer(('127.0.0.1', 0), partial(StaticHTTP, directory=str(ROOT / 'section_0_app/src')))
    threads = [threading.Thread(target=http.serve_forever, daemon=True) for http in (model_http, static_http)]
    for thread in threads:
        thread.start()
    app_root = tmp_path / 'app'
    app_root.mkdir()
    for section in ROOT.glob('section_*'):
        if section.is_dir():
            shutil.copytree(section, app_root / section.name,
                            ignore=shutil.ignore_patterns('node_modules', 'target', '__pycache__', 'entries'))
    (app_root / 'section_7_models/models_registry.yaml').write_text(yaml.safe_dump({'llms': {
        'test-provider': {'provider': 'ollama', 'model_name': 'fixture-resource:latest',
                          'api_url': f'http://127.0.0.1:{model_http.server_port}', 'installed': True},
    }}))
    memory = Memory(tmp_path / 'memory')
    monkeypatch.setattr('section_3_memory.api.Memory', lambda: memory)
    original_mind = server.CentralMind
    def construct(**kwargs):
        mind = original_mind(**kwargs)
        events['minds'].append(mind)
        return mind
    monkeypatch.setattr(server, 'CentralMind', construct)
    auth = AuthService(tmp_path / 'private/auth.sqlite3')
    auth.bootstrap_admin('test_admin', 'Test-admin-password-1')
    admin = auth.login('test_admin', 'Test-admin-password-1')
    auth.create_account(admin['token'], 'test_trainer', 'Test-trainer-password-2', role='trainer')
    loop = asyncio.new_event_loop()
    started = threading.Event()
    state = {}
    def serve():
        asyncio.set_event_loop(loop)
        async def start():
            runtimes = server.SessionRuntimes(auth)
            async def handler(ws):
                await server.handle_client(ws, app_root, auth_service=auth, runtimes=runtimes)
            state['service'] = await websockets.serve(handler, '127.0.0.1', 0)
            state['port'] = state['service'].sockets[0].getsockname()[1]
            started.set()
        loop.run_until_complete(start())
        loop.run_forever()
    ws_thread = threading.Thread(target=serve, daemon=True)
    ws_thread.start()
    assert started.wait(10)
    try:
        yield {'events': events, 'project': project, 'memory': memory, 'app_root': app_root,
               'url': f'http://127.0.0.1:{static_http.server_port}',
               'ws': f"ws://127.0.0.1:{state['port']}"}
    finally:
        async def stop():
            state['service'].close()
            await state['service'].wait_closed()
        asyncio.run_coroutine_threadsafe(stop(), loop).result(15)
        loop.call_soon_threadsafe(loop.stop)
        ws_thread.join(5)
        for http, thread in zip((model_http, static_http), threads):
            http.shutdown(); http.server_close(); thread.join(5)


def test_browser_clarification_coding_repair_and_shared_window_refresh(browser_stack):
    from playwright.sync_api import sync_playwright, expect
    stack = browser_stack
    errors = []
    native_state = {'token': None}
    def native_bridge(command, args=None):
        if command == 'set_application_session':
            native_state['token'] = args['token']
        if command == 'get_application_session':
            return native_state['token']
        if command == 'clear_application_session':
            native_state['token'] = None
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=shutil.which('chromium'), headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        context.expose_function('nativeBridge', native_bridge)
        context.add_init_script('''
            const NativeSocket = window.WebSocket;
            window.WebSocket = class extends NativeSocket {
                constructor(url, protocols) {
                    super(url === 'ws://127.0.0.1:8765' ? %s : url, protocols);
                }
            };
            window.__TAURI__ = {
                core: {invoke: (command, args) => window.nativeBridge(command, args)},
                dialog: {open: async () => %s},
            };
        ''' % (json.dumps(stack['ws']), json.dumps(str(stack['project']))))
        chat = context.new_page()
        chat.on('pageerror', lambda error: errors.append(str(error)))
        chat.goto(stack['url'] + '/window-chat.html')
        chat.locator('#auth-username').fill('test_trainer')
        chat.locator('#auth-password').fill('Test-trainer-password-2')
        chat.locator('#auth-form button').click()
        expect(chat.locator('#auth-overlay')).to_be_hidden(timeout=15000)
        coding = context.new_page()
        coding.on('pageerror', lambda error: errors.append(str(error)))
        coding.goto(stack['url'] + '/window-code.html')
        expect(coding.locator('#auth-overlay')).to_be_hidden(timeout=15000)
        coding.locator('#btn-open-folder').click()
        expect(coding.locator('#files-tree')).to_contain_text('answer.py')
        coding.locator('#files-tree .file').filter(has_text='🐍 answer.py').click()
        expect(coding.locator('#editor')).to_contain_text('return 0')
        assert len(stack['events']['minds']) == 1, 'windows must share their authenticated Mind'
        chat.locator('#input').fill('Fix answer.py to return the value I want')
        chat.locator('#send').click()
        expect(chat.locator('#chat-thread')).to_contain_text('What value should answer() return?', timeout=15000)
        expect(chat.locator('#send')).to_be_enabled()
        assert (stack['project'] / 'answer.py').read_text().endswith('return 0\n')
        chat.locator('#input').fill('42')
        chat.locator('#send').click()
        expect(chat.locator('#send')).to_be_disabled()
        expect(chat.locator('#chat-thread')).to_contain_text('Functional tests: 1 run, 1 passed', timeout=60000)
        expect(chat.locator('#send')).to_be_enabled()
        expect(chat.locator('.msg-artifacts').last).to_contain_text('answer.py')
        expect(coding.locator('#editor')).to_contain_text('return 42', timeout=15000)
        assert stack['events']['repair_saw_original'], 'failed candidate must not be written to the project'
        assert stack['events']['communication_evidence'][-1]
        assert (stack['project'] / 'answer.py').read_text().endswith('return 42\n')
        entries = list(stack['memory'].store.iter_entries())
        assert entries and all(entry.memory_class != 'raw' for entry in entries)
        coding.get_by_role('button', name='Run Python tests', exact=True).click()
        expect(coding.locator('#terminal')).to_contain_text('1 passed', timeout=30000)
        screenshot = ROOT / 'test_results/ui-round-trip.png'
        screenshot.parent.mkdir(exist_ok=True)
        chat.screenshot(path=str(screenshot), full_page=True)
        assert not errors, errors
        browser.close()
