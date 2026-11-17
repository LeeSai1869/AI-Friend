from types import SimpleNamespace
import pytest
from section_4_chatbox.runtime import ChatRuntime


def test_histories_and_explicit_deletion_are_scoped_to_authenticated_owner(tmp_path):
    mind = SimpleNamespace(process=lambda *args, **kwargs: {'status': 'ok', 'output': 'Hello'})
    alice = ChatRuntime(mind, tmp_path, owner='Alice')
    bob = ChatRuntime(mind, tmp_path, owner='Bob')
    chat = alice.respond('My private topic')
    chat_id = chat['chat_id']
    assert alice.load_chat(chat_id)
    assert bob.list_chats() == []
    assert bob.load_chat(chat_id) is None
    assert not bob.delete_chat(chat_id)
    assert alice.load_chat(chat_id)
    assert alice.delete_chat(chat_id)
    assert not alice.list_chats()
    assert alice.load_chat(chat_id) is None
    assert not alice.delete_chat(chat_id)


def test_delete_rejects_traversal_and_symlink_and_keeps_other_data(tmp_path):
    runtime = ChatRuntime(None, tmp_path, owner='alice')
    marker = tmp_path / 'project.py'
    marker.write_text('keep me')
    with pytest.raises(ValueError):
        runtime.delete_chat('../../project.py')
    link = runtime.store.root / 'chat_link'
    link.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError):
        runtime.delete_chat('chat_link')
    assert runtime.load_chat('chat_link') is None
    assert runtime.list_chats() == []
    assert marker.read_text() == 'keep me'


def test_legacy_unowned_chats_are_preserved_but_not_assigned_to_an_arbitrary_user(tmp_path):
    legacy = ChatRuntime(None, tmp_path)
    old = legacy.open_chat()
    scoped = ChatRuntime(None, tmp_path, owner='new-user')
    assert scoped.load_chat(old.chat_id) is None
    assert legacy.load_chat(old.chat_id)


def test_response_feedback_is_persisted_and_owner_scoped(tmp_path):
    mind = SimpleNamespace(process=lambda *args, **kwargs: {'status': 'ok', 'output': 'Answer'})
    alice = ChatRuntime(mind, tmp_path, owner='Alice')
    bob = ChatRuntime(mind, tmp_path, owner='Bob')
    response = alice.respond('Question')

    recorded = alice.record_feedback(
        response['chat_id'], turn_index=1, rating='not_helpful',
        comment='The answer omitted the requested test result.',
    )
    saved = alice.load_chat(response['chat_id'])
    assert recorded['ok']
    assert saved['turns'][1]['feedback']['rating'] == 'not_helpful'
    assert saved['turns'][1]['feedback']['comment'] == (
        'The answer omitted the requested test result.'
    )
    with pytest.raises(ValueError, match='chat not found'):
        bob.record_feedback(
            response['chat_id'], turn_index=1, rating='helpful'
        )
    with pytest.raises(ValueError, match='Central Mind response'):
        alice.record_feedback(
            response['chat_id'], turn_index=0, rating='helpful'
        )


def test_chat_runtime_delivers_failure_receipt_without_reporting_success(tmp_path):
    receipt = {
        'candidate_applied': False,
        'failing_tests': [{
            'name': 'tests/test_answer.py::test_answer',
            'assertion': 'AssertionError: expected 42, got 41',
        }],
    }
    mind = SimpleNamespace(process=lambda *args, **kwargs: {
        'status': 'error',
        'error': 'functional tests failed after the repair budget',
        'output': 'No candidate was applied. test_answer failed.',
        'execution_receipt': receipt,
    })
    runtime = ChatRuntime(mind, tmp_path, owner='Alice')

    response = runtime.respond('Create the answer')

    assert response['status'] == 'error'
    assert response['ok'] is False
    assert 'No candidate was applied' in response['text']
    assert response['execution_receipt'] == receipt


def test_explicit_legacy_access_allows_cleanup_without_assigning_ownership(tmp_path):
    legacy = ChatRuntime(None, tmp_path)
    old = legacy.open_chat()
    old.set_topic('Old unowned topic')
    admin = ChatRuntime(None, tmp_path, owner='admin', include_legacy=True)
    trainer = ChatRuntime(None, tmp_path, owner='trainer')
    assert admin.list_chats()[0]['legacy'] is True
    assert 'Older, unassigned' in admin.list_chats()[0]['topic']
    assert admin.load_chat(old.chat_id)
    assert trainer.load_chat(old.chat_id) is None
    assert not trainer.delete_chat(old.chat_id)
    assert admin.delete_chat(old.chat_id)
    assert legacy.load_chat(old.chat_id) is None
