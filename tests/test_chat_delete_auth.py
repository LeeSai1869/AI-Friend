import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "section_1_central_mind"))
import bootstrap
import server
from section_4_chatbox.runtime import ChatRuntime
from tests.test_server_auth_security import FakeWebSocket, SafeFakeMind


def test_server_uses_authenticated_owner_and_ignores_client_owner_claims(tmp_path):
    auth = server.AuthService(tmp_path / 'private/auth.sqlite3')
    auth.bootstrap_admin('test_admin', 'Test-password-long-1')
    admin = auth.login('test_admin', 'Test-password-long-1')
    auth.create_account(admin['token'], 'test_user', 'Test-password-long-2', role='user')
    legacy = ChatRuntime(None, tmp_path).open_chat()
    victim = ChatRuntime(None, tmp_path, owner='test_admin').open_chat()
    owned = ChatRuntime(None, tmp_path, owner='test_user').open_chat()
    ws = FakeWebSocket([
        {'op': 'delete_chat', 'chat_id': owned.chat_id},
        {'op': 'login', 'username': 'test_user', 'password': 'Test-password-long-2'},
        {'op': 'delete_chat', 'chat_id': victim.chat_id, 'owner': 'test_admin', 'role': 'administrator'},
        {'op': 'delete_chat', 'chat_id': legacy.chat_id, 'include_legacy': True},
        {'op': 'delete_chat', 'chat_id': owned.chat_id},
    ])
    with patch.object(server, 'CentralMind', SafeFakeMind):
        asyncio.run(server.handle_client(ws, tmp_path, auth_service=auth))
    assert ws.sent[0]['op'] == 'auth_required'
    results = [msg for msg in ws.sent if msg.get('op') == 'chat_deleted']
    assert [msg['ok'] for msg in results] == [False, False, True]
    assert ChatRuntime(None, tmp_path, owner='test_admin').load_chat(victim.chat_id)
    assert ChatRuntime(None, tmp_path).load_chat(legacy.chat_id)


def test_chat_feedback_requires_owned_chat_and_persists_on_response(tmp_path):
    auth = server.AuthService(tmp_path / 'private/auth.sqlite3')
    auth.bootstrap_admin('test_admin', 'Test-password-long-1')
    admin = auth.login('test_admin', 'Test-password-long-1')
    auth.create_account(admin['token'], 'test_user', 'Test-password-long-2', role='user')

    owner_runtime = ChatRuntime(None, tmp_path, owner='test_user')
    chat = owner_runtime.open_chat()
    chat.add_turn('user', 'Question')
    chat.add_turn('mind', 'Answer')
    foreign_chat = ChatRuntime(None, tmp_path, owner='test_admin').open_chat()
    ws = FakeWebSocket([
        {'op': 'chat_feedback', 'chat_id': chat.chat_id, 'turn_index': 1, 'rating': 'helpful'},
        {'op': 'login', 'username': 'test_user', 'password': 'Test-password-long-2'},
        {'op': 'chat_feedback', 'chat_id': foreign_chat.chat_id, 'turn_index': 1, 'rating': 'helpful'},
        {'op': 'chat_feedback', 'chat_id': chat.chat_id, 'turn_index': 1,
         'rating': 'not_helpful', 'comment': 'Missing the test output'},
    ])
    with patch.object(server, 'CentralMind', SafeFakeMind):
        asyncio.run(server.handle_client(ws, tmp_path, auth_service=auth))

    assert ws.sent[0]['op'] == 'auth_required'
    feedback_results = [msg for msg in ws.sent if msg.get('op') == 'chat_feedback_result']
    assert [msg['ok'] for msg in feedback_results] == [False, True]
    saved = owner_runtime.load_chat(chat.chat_id)
    assert saved['turns'][1]['feedback']['rating'] == 'not_helpful'
    assert saved['turns'][1]['feedback']['comment'] == 'Missing the test output'
