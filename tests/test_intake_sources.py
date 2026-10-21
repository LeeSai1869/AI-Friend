import json
from types import SimpleNamespace
import pytest
from section_8_tools.intake.intake import IntakePropose, MAX_CONTENT_BYTES


def test_import_text_preserves_entire_source_and_uses_capability_routing(tmp_path):
    calls = []
    def route(domain, capability, **kwargs):
        calls.append((domain, capability))
        return json.dumps({'title': 'A lesson', 'domain': 'Gen', 'kind': 'fact', 'tags': ['lesson']})
    content = 'Training source. ' * 1000
    tool = IntakePropose(tmp_path, None)
    result = tool.call({'source': {'kind': 'text', 'name': 'Lesson', 'content': content},
                        'caller': SimpleNamespace(route=route)})
    assert result['ok']
    proposal = result['data']['proposal']
    assert proposal['content'] == content
    assert len(proposal['preview']) == 500
    assert proposal['content_bytes'] == len(content.encode())
    assert calls == [('general', 'reason')]
    assert not list(tmp_path.iterdir()), 'proposal preparation must not write global pending state'


def test_external_folder_upload_preserves_provenance_without_reading_host_paths(tmp_path):
    tool = IntakePropose(tmp_path, None)
    args = {'source': {'kind': 'folder', 'name': 'training', 'files': [
        {'name': '/external/lesson.txt', 'content': 'Training text'},
        {'name': 'second.md', 'content': 'Other text'},
    ]}}
    assert [effect.action for effect in tool.effects(args)] == ['service']
    result = tool.call(args)
    assert result['ok']
    proposal = result['data']['proposal']
    assert 'Training text' in proposal['content'] and 'Other text' in proposal['content']
    assert len(proposal['source_files']) == 2
    assert len(proposal['source_files'][0]['sha256']) == 64


@pytest.mark.parametrize('source', [
    {'kind': 'file', 'content': 'binary\x00'},
    {'kind': 'text', 'content': ''},
    {'kind': 'text', 'content': 'a' * (MAX_CONTENT_BYTES + 1)},
    {'kind': 'folder', 'files': [{'content': 'x'}] * 51},
])
def test_binary_empty_and_oversized_sources_are_rejected(tmp_path, source):
    assert not IntakePropose(tmp_path, None).call({'source': source})['ok']


def test_workspace_folder_rejects_symlink_escape(tmp_path):
    folder = tmp_path / 'training'
    folder.mkdir()
    (folder / 'outside.txt').symlink_to('/etc/passwd')
    tool = IntakePropose(tmp_path, None)
    result = tool.call({'path': 'training'})
    assert not result['ok'] and 'symlink' in result['error']


def test_no_model_can_still_prepare_source_for_manual_review_without_claiming_classification(tmp_path):
    def fail(*args, **kwargs):
        raise RuntimeError('unreachable')
    result = IntakePropose(tmp_path, None).call({'source': {'kind': 'text', 'name': 'Lesson', 'content': 'Text'},
                                               'caller': SimpleNamespace(route=fail)})
    assert result['ok']
    assert 'unavailable' in result['data']['proposal']['warning']
