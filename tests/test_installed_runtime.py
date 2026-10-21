from types import SimpleNamespace
from pathlib import Path
from section_1_central_mind.guard.resources import ResourceClassifier
from section_4_chatbox.runtime import ChatRuntime
from section_5_domains.coding.tree.tree import ProjectTree
from section_5_domains.coding.workspace import CodingWorkspace
from section_5_domains.coding.project.project import CodingProject

ROOT = Path(__file__).resolve().parents[1]


def test_persistent_memory_stays_protected_even_when_its_parent_is_open_as_a_project(tmp_path, monkeypatch):
    source = tmp_path / 'bundle'
    source.mkdir()
    state = tmp_path / 'private-state'
    state.mkdir()
    monkeypatch.setenv('AI_FRIEND_STATE_DIR', str(state))
    classifier = ResourceClassifier(source, SimpleNamespace(all=lambda: []), workspace_root=state)
    assert classifier.classify(state / 'memory/entries/entry.json').kind == 'memory'
    assert classifier.classify(state / 'notes.txt').kind == 'workspace'
    runtime = ChatRuntime(None, source, owner='trainer')
    chat = runtime.open_chat()
    assert chat.root.is_relative_to(state)
    assert not (source / '.central_mind').exists()


def test_explorer_lists_assets_and_lockfiles_but_reasoning_inventory_excludes_binary(tmp_path):
    (tmp_path / 'assets').mkdir()
    (tmp_path / 'assets/image.png').write_bytes(b'\x89PNG\x00')
    (tmp_path / 'package.lock').write_text('dependency data')
    (tmp_path / 'assets/info.txt').write_text('text')
    tree = ProjectTree(CodingWorkspace(CodingProject.open(tmp_path)))
    assert any(item['name'] == 'package.lock' for item in tree.list())
    assert {item['name'] for item in tree.list('assets')} == {'image.png', 'info.txt'}
    assert 'assets/info.txt' in tree.files()
    assert 'assets/image.png' not in tree.files()


def test_frontend_and_backend_release_identifiers_match():
    from section_1_central_mind.runtime_identity import BUILD_ID
    assert f'"{BUILD_ID}"' in (ROOT / 'section_0_app/src/ui/shared/build.js').read_text()
