import json
import re
from pathlib import Path

from section_3_memory.api import Memory


def test_memory_entries_persist_in_their_class_folders(tmp_path):
    memory = Memory(root=tmp_path)
    raw = memory.record(
        domain="Gen",
        kind="fact",
        title="A raw lesson",
        content="Unverified source text.",
        memory_class="raw",
    )
    tested = memory.record(
        domain="Cod",
        kind="success",
        title="A tested result",
        content="Verified behavior.",
        memory_class="tested",
    )
    derived = memory.record(
        domain="Mind",
        kind="theory",
        title="A derived rule",
        content="A reusable conclusion.",
        memory_class="derived",
    )

    assert re.fullmatch(r"raw_a-raw-lesson_[a-z]{8}", raw.id)
    assert tested.id.startswith("mem_Cod_")
    assert derived.id.startswith("mem_Mind_")
    assert (tmp_path / "Raw Memory" / f"{raw.id}.json").is_file()
    assert (tmp_path / "Tested Memory" / f"{tested.id}.json").is_file()
    assert (tmp_path / "Derived Memory" / f"{derived.id}.json").is_file()

    restored = Memory(root=tmp_path)
    assert restored.count() == 3
    assert restored.get(raw.id).content == "Unverified source text."
    assert restored.get(tested.id).content == "Verified behavior."
    assert restored.get(derived.id).content == "A reusable conclusion."


def test_legacy_entries_are_copied_to_class_folder_without_deletion(tmp_path):
    legacy_dir = tmp_path / "entries"
    legacy_dir.mkdir()
    legacy_path = legacy_dir / "mem_Cod_0000000000007.json"
    legacy_path.write_text(json.dumps({
        "id": "mem_Cod_0000000000007",
        "ts": 1,
        "domain_created": "Cod",
        "memory_class": "tested",
        "kind": "success",
        "title": "Legacy memory",
        "content": "Preserve this exact content.",
    }), encoding="utf-8")

    memory = Memory(root=tmp_path)

    migrated_path = (
        tmp_path / "Tested Memory" / "mem_Cod_0000000000007.json"
    )
    assert migrated_path.read_bytes() == legacy_path.read_bytes()
    assert legacy_path.is_file()
    assert memory.get("mem_Cod_0000000000007").content == (
        "Preserve this exact content."
    )


def test_legacy_raw_entries_get_non_sequential_ids_and_rewrite_references(tmp_path):
    legacy_dir = tmp_path / "entries"
    legacy_dir.mkdir()
    raw_id = "mem_Gen_0000000000004"
    (legacy_dir / f"{raw_id}.json").write_text(json.dumps({
        "id": raw_id,
        "ts": 1,
        "domain_created": "Gen",
        "memory_class": "raw",
        "kind": "fact",
        "title": "Imported source",
        "content": "Full unverified source.",
        "source_refs": [],
        "source": {},
    }), encoding="utf-8")
    tested_id = "mem_Cod_0000000000003"
    (legacy_dir / f"{tested_id}.json").write_text(json.dumps({
        "id": tested_id,
        "ts": 2,
        "domain_created": "Cod",
        "memory_class": "tested",
        "kind": "success",
        "title": "Tested passage",
        "content": "Verified passage.",
        "source_refs": [raw_id],
        "cross_refs": [{"ref": raw_id, "reason": "derived_from"}],
    }), encoding="utf-8")

    memory = Memory(root=tmp_path)

    raw_entries = list((tmp_path / "Raw Memory").glob("*.json"))
    assert len(raw_entries) == 1
    migrated_raw = json.loads(raw_entries[0].read_text(encoding="utf-8"))
    assert migrated_raw["id"].startswith("raw_imported-source_")
    assert migrated_raw["source"]["legacy_id"] == raw_id
    assert memory.get(raw_id).id == migrated_raw["id"]
    assert memory.count() == 2
    tested = memory.get(tested_id)
    assert tested.source_refs == [migrated_raw["id"]]
    assert tested.cross_refs[0].ref == migrated_raw["id"]

    restored = Memory(root=tmp_path)
    assert restored.count() == 2
    assert restored.get(raw_id).id == migrated_raw["id"]
    assert list((tmp_path / "Raw Memory").glob("*.json")) == raw_entries


def test_raw_intake_adds_new_entries_without_overwriting_existing_raw(tmp_path):
    memory = Memory(root=tmp_path)
    first = memory.record(
        domain="Gen",
        kind="fact",
        title="Trainer source",
        content="First version.",
        memory_class="raw",
    )
    second = memory.record(
        domain="Gen",
        kind="fact",
        title="Trainer source",
        content="Updated source from a new intake.",
        memory_class="raw",
    )

    assert first.id != second.id
    assert memory.get(first.id).content == "First version."
    assert memory.get(second.id).content == "Updated source from a new intake."
    assert memory.count() == 2
