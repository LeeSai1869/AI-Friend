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
