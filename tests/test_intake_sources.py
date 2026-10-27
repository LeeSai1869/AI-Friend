import json
import hashlib
from types import SimpleNamespace
import pytest
from section_8_tools.intake.intake import IntakePropose


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
    assert proposal['intake_questions'][0].lower().startswith("what is the nature")
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
    expected_content = (
        '----- /external/lesson.txt -----\nTraining text\n\n'
        '----- second.md -----\nOther text'
    )
    assert proposal['content'] == expected_content
    assert len(proposal['source_files']) == 2
    assert len(proposal['source_files'][0]['sha256']) == 64
    assert proposal['content_bytes'] == len(expected_content.encode('utf-8'))
    assert proposal['source_sha256'] == hashlib.sha256(
        expected_content.encode('utf-8')
    ).hexdigest()


def test_large_text_and_more_than_fifty_files_are_accepted(tmp_path):
    large_content = 'a' * (512 * 1024 + 1)
    large_result = IntakePropose(tmp_path, None).call({
        'source': {'kind': 'text', 'content': large_content},
    })
    assert large_result['ok']
    assert large_result['data']['proposal']['content'] == large_content

    files = [
        {'name': f'lesson-{index}.txt', 'content': f'lesson {index}'}
        for index in range(51)
    ]
    folder_result = IntakePropose(tmp_path, None).call({
        'source': {'kind': 'folder', 'name': 'training', 'files': files},
    })
    assert folder_result['ok']
    assert len(folder_result['data']['proposal']['source_files']) == 51


@pytest.mark.parametrize('source', [
    {'kind': 'file', 'content': 'binary\x00'},
    {'kind': 'text', 'content': ''},
])
def test_binary_and_empty_sources_are_rejected(tmp_path, source):
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
