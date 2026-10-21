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
                assert request.get('format') == 'json', 'Mind JSON requirement must reach the provider'
                payload = json.loads(request['messages'][-1]['content'])
                objective = payload['objective']
                pending = payload['supplied_context'].get('pending_clarification')
                reading = 'read my ptoject files' in objective.lower()
                needs_answer = '42' not in objective and not objective.lower().startswith('hello') and not reading
                greeting = objective.lower().startswith('hello')
                steps = [] if needs_answer else ([{
                    'step_id': 'say', 'objective': 'Greet the user', 'kind': 'communicate',
                    'component': None, 'capability': None, 'depends_on': [], 'confidence': .95,
                }] if greeting else [
                    {'step_id': 'implement', 'objective': objective if reading else 'Fix answer.py so answer() returns 42',
                     'kind': 'domain', 'component': 'coder', 'capability': 'inspect_code' if reading else 'write_code',
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
            elif 'Classify this untrusted training source' in text:
                output = json.dumps({'domain': 'Gen', 'kind': 'fact', 'title': 'Imported lesson', 'tags': ['training']})
            elif 'Select the existing files most relevant' in text:
                output = json.dumps({'files': ['answer.py'], 'reason': 'Inspect the project implementation'})
            elif 'Files actually inspected:' in text:
                assert 'def answer()' in text
                output = 'I read answer.py from the open project. It defines answer() and returns 42.'
            elif "Render Central Mind's final response" in text:
                payload = json.loads(request['messages'][-1]['content'])
                events['communication_evidence'].append(payload['verified_evidence'])
                output = ('I read answer.py from the open project.\n' if 'ptoject' in payload.get('objective', '') else 'Implemented answer.py and verified the selected behavior.\n') + '\n'.join(payload['verified_evidence']) if payload['verified_evidence'] else 'Hello. How can I help?'
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
    native_state = {'token': None, 'saved': None}
    def native_bridge(command, args=None):
        if command == 'set_application_session':
            native_state['token'] = args['token']
            native_state['saved'] = args['token'] if args.get('remember') else None
        if command == 'get_application_session':
            return native_state['token'] or native_state['saved']
        if command == 'clear_application_session':
            native_state['token'] = None
            native_state['saved'] = None
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=shutil.which('chromium'), headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        context.expose_function('nativeBridge', native_bridge)
        native_script = '''
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
        ''' % (json.dumps(stack['ws']), json.dumps(str(stack['project'])))
        context.add_init_script(native_script)
        chat = context.new_page()
        chat.on('pageerror', lambda error: errors.append(str(error)))
        chat.goto(stack['url'] + '/window-chat.html')
        chat.locator('#auth-username').fill('test_trainer')
        chat.locator('#auth-password').fill('Test-trainer-password-2')
        chat.locator('#auth-remember').check()
        chat.locator('#auth-form button').click()
        expect(chat.locator('#auth-overlay')).to_be_hidden(timeout=15000)
        expect(chat.locator('#runtime-build')).to_contain_text('UI / Mind connected')
        assert native_state['saved']
        coding = context.new_page()
        coding.on('pageerror', lambda error: errors.append(str(error)))
        coding.goto(stack['url'] + '/window-code.html')
        expect(coding.locator('#auth-overlay')).to_be_hidden(timeout=15000)
        (stack['project'] / 'assets').mkdir()
        (stack['project'] / 'assets/image.png').write_bytes(b'PNG')
        (stack['project'] / 'assets/info.txt').write_text('Nested text file')
        coding.locator('#btn-open-folder').click()
        expect(coding.locator('#files-tree')).to_contain_text('answer.py')
        coding.locator('#files-tree .file').filter(has_text='assets').click()
        expect(coding.locator('#files-tree')).to_contain_text('image.png')
        expect(coding.locator('#files-tree')).to_contain_text('info.txt')
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
        # Reproduce the user's project-read request through the actual loop.
        chat.locator('#btn-new-chat').click()
        chat.locator('#input').fill('Can you read my ptoject files?')
        chat.locator('#send').click()
        expect(chat.locator('#chat-thread')).to_contain_text('I read answer.py from the open project.', timeout=30000)
        expect(chat.locator('#send')).to_be_enabled()
        assert (stack['project'] / 'answer.py').read_text().endswith('return 42\n')

        # Explicit deletion propagates to both windows and leaves source intact.
        coding.locator('.coding-history-item').filter(has_text='Can you read my ptoject files?').click()
        expect(coding.locator('#chat-thread')).to_contain_text('I read answer.py')
        chat.get_by_role('button', name='Chat actions: Can you read my ptoject files?', exact=True).click()
        chat.get_by_role('menuitem', name='Delete chat', exact=True).click()
        expect(chat.locator('#chat-list')).not_to_contain_text('Can you read my ptoject files?')
        expect(coding.locator('#coding-chat-history')).not_to_contain_text('Can you read my ptoject files?')
        expect(coding.locator('#chat-thread')).not_to_contain_text('I read answer.py')
        assert (stack['project'] / 'answer.py').exists()

        # All four extra intake methods are connected, including a source outside the project.
        chat.locator('#btn-intake').click()
        chat.locator('[data-action="text"]').click()
        lesson = 'Learning material. ' * 100 + 'END-OF-FULL-SOURCE'
        chat.locator('#intake-source').fill(lesson)
        chat.locator('#intake-source-name').fill('External lesson')
        chat.locator('#intake-source-submit').click()
        expect(chat.locator('#intake-store')).to_be_visible(timeout=15000)
        chat.locator('#intake-store').click()
        expect(chat.locator('#intake-body')).to_contain_text('Intake evaluation result', timeout=15000)
        proposal_id = int(chat.locator('.intake-value').first.inner_text())
        imported = stack['events']['minds'][0].memory_service.knowledge_proposal(proposal_id)
        assert imported['content'] == lesson, 'must ingest full content, not its 500-character preview'
        chat.locator('#intake-another').click()
        chat.locator('[data-action="file"]').click()
        chat.locator('#intake-upload').set_input_files({'name': 'outside-project.txt', 'mimeType': 'text/plain', 'buffer': b'External disk lesson'})
        chat.locator('#intake-upload-submit').click()
        expect(chat.locator('.intake-preview')).to_contain_text('External disk lesson', timeout=15000)
        chat.locator('#intake-back-2').click()
        chat.locator('[data-action="folder"]').click()
        folder = stack['project'].parent / 'training-folder'
        folder.mkdir()
        (folder / 'lesson.md').write_text('Folder training lesson')
        # Directory chooser plumbing is native/browser-specific. Supply its
        # standard FileList result, then exercise the production reader and socket.
        chat.locator('#intake-upload').evaluate("""input => {
            const file = new File(['Folder training lesson'], 'lesson.md', {type:'text/markdown'});
            Object.defineProperty(file, 'webkitRelativePath', {value:'training-folder/lesson.md'});
            const files = new DataTransfer(); files.items.add(file); input.files = files.files;
        }""")
        chat.locator('#intake-upload-submit').click()
        expect(chat.locator('.intake-preview')).to_contain_text('Folder training lesson', timeout=15000)
        chat.locator('#intake-back-2').click()
        chat.locator('[data-action="url"]').click()
        chat.locator('#intake-source').fill(stack['url'] + '/window-chat.html')
        chat.locator('#intake-source-submit').click()
        expect(chat.locator('#intake-store')).to_be_visible(timeout=15000)
        drafts = stack['events']['minds'][0]._intake_drafts.values()
        assert any(draft['source_kind'] == 'url' and draft['source_path'].endswith('/window-chat.html') for draft in drafts)
        chat.locator('#intake-cancel-2').click()
        chat.locator('#btn-new-chat').click()
        chat.locator('#input').fill('Hello')
        chat.locator('#send').click()
        expect(chat.locator('#chat-thread')).to_contain_text('Hello. How can I help?', timeout=15000)
        expect(chat.locator('.msg-tool')).to_have_count(0)
        screenshot = ROOT / 'test_results/ui-round-trip.png'
        screenshot.parent.mkdir(exist_ok=True)
        chat.screenshot(path=str(screenshot), full_page=True)
        assert not errors, errors
        # Recreate the UI/native in-memory session while retaining only the
        # Keychain fixture. The real backend must validate the saved credential.
        context.close()
        native_state['token'] = None
        restored = browser.new_context()
        restored.expose_function('nativeBridge', native_bridge)
        restored.add_init_script(native_script)
        page = restored.new_page()
        page.goto(stack['url'] + '/window-chat.html')
        expect(page.locator('#auth-overlay')).to_be_hidden(timeout=15000)
        expect(page.locator('#runtime-build')).to_contain_text('UI / Mind connected')
        assert page.evaluate('localStorage.length') == 0
        browser.close()
