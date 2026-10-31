"""File-backed storage for Raw, Tested, and Derived Memory entries."""
from __future__ import annotations

import json
import re
import shutil
import threading
from pathlib import Path
from typing import Iterator, List, Optional

from . import config
from .entry import Entry, make_raw_id


class Store:

    def __init__(self, memory_root: Path = None):
        self.memory_root = Path(memory_root or config.MEMORY_ROOT)
        self.entries_dir = self.memory_root / "entries"
        self._class_directories = {
            memory_class: self.memory_root / directory_name
            for memory_class, directory_name
            in config.MEMORY_CLASS_DIRECTORIES.items()
        }
        for directory in self._class_directories.values():
            directory.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._legacy_aliases = self._preserve_legacy_entries()

    def _class_directory(self, memory_class: str) -> Path:
        try:
            return self._class_directories[memory_class]
        except KeyError as exc:
            raise ValueError(f"unknown memory class: {memory_class!r}") from exc

    @staticmethod
    def _validate_id(mem_id: str) -> None:
        domains = "|".join(re.escape(prefix) for prefix in config.DOMAIN_PREFIXES)
        legacy_pattern = (
            rf"{re.escape(config.ID_PREFIX)}_"
            rf"(?:{domains})_"
            rf"\d{{{config.SEQUENCE_DIGITS}}}"
        )
        raw_pattern = r"raw_[a-z0-9-]+_[a-z]{8}"
        if (
            not isinstance(mem_id, str)
            or re.fullmatch(legacy_pattern, mem_id) is None
            and re.fullmatch(raw_pattern, mem_id) is None
        ):
            raise ValueError(f"invalid memory ID: {mem_id!r}")

    def _path_for(
        self,
        mem_id: str,
        memory_class: Optional[str] = None,
    ) -> Path:
        self._validate_id(mem_id)
        if memory_class is None:
            return self.entries_dir / f"{mem_id}.json"
        if mem_id.startswith("raw_") and memory_class != "raw":
            raise ValueError("Raw Memory identifiers must be stored as raw")
        if not mem_id.startswith("raw_") and memory_class == "raw":
            # Existing numbered Raw entries retain their IDs during migration.
            pass
        return self._class_directory(memory_class) / f"{mem_id}.json"

    def _read_payload(self, path: Path) -> dict:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                f"Cannot preserve memory entry {path}: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise RuntimeError(f"Cannot preserve memory entry {path}: expected an object")
        return payload

    def _write_payload(self, path: Path, payload: dict) -> None:
        temp = path.with_suffix(".tmp")
        temp.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temp.replace(path)

    def _preserve_legacy_entries(self) -> dict[str, str]:
        aliases = {}
        raw_directory = self._class_directory("raw")

        for path in raw_directory.glob("raw_*.json"):
            payload = self._read_payload(path)
            source = payload.get("source")
            legacy_id = source.get("legacy_id") if isinstance(source, dict) else None
            if isinstance(legacy_id, str):
                aliases[legacy_id] = payload["id"]

        for path in raw_directory.glob("mem_*.json"):
            payload = self._read_payload(path)
            old_id = payload.get("id")
            if payload.get("memory_class") != "raw" or not isinstance(old_id, str):
                raise RuntimeError(
                    f"Cannot migrate Raw Memory entry {path}: invalid entry metadata"
                )
            aliases[old_id] = self._migrate_raw_payload(
                payload,
                path,
                raw_directory,
                old_id,
            )

        if self.entries_dir.is_dir():
            for legacy_path in self.entries_dir.glob("mem_*.json"):
                payload = self._read_payload(legacy_path)
                memory_class = payload.get("memory_class")
                if memory_class not in self._class_directories:
                    raise RuntimeError(
                        f"Cannot preserve legacy memory entry {legacy_path}: "
                        f"invalid memory_class {memory_class!r}"
                    )
                old_id = legacy_path.stem
                if memory_class == "raw":
                    if old_id not in aliases:
                        aliases[old_id] = self._migrate_raw_payload(
                            payload,
                            legacy_path,
                            raw_directory,
                            old_id,
                        )
                    continue
                destination = self._path_for(old_id, memory_class)
                if not destination.exists():
                    shutil.copy2(legacy_path, destination)

        self._rewrite_raw_references(aliases)
        return aliases

    def _migrate_raw_payload(
        self,
        payload: dict,
        source_path: Path,
        raw_directory: Path,
        old_id: str,
    ) -> str:
        source = payload.get("source")
        source = dict(source) if isinstance(source, dict) else {}
        existing_legacy_id = source.get("legacy_id")
        if isinstance(existing_legacy_id, str):
            return payload["id"]

        while True:
            new_id = make_raw_id(str(payload.get("title") or "memory"))
            destination = self._path_for(new_id, "raw")
            if not destination.exists():
                break

        source["legacy_id"] = old_id
        migrated = dict(payload)
        migrated["id"] = new_id
        migrated["source"] = source
        self._write_payload(destination, migrated)

        if source_path.parent == raw_directory:
            legacy_backup = self._path_for(old_id)
            if not legacy_backup.exists():
                self.entries_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, legacy_backup)
            source_path.unlink()

        return new_id

    def _rewrite_raw_references(self, aliases: dict[str, str]) -> None:
        # An old Raw number may already have been reused by a canonical
        # Tested/Derived record. Never guess which record a reference meant.
        aliases = {old:new for old,new in aliases.items() if not any(
            (self._class_directory(cls) / f"{old}.json").is_file()
            for cls in ("tested", "derived"))}
        if not aliases:
            return
        for directory in self._class_directories.values():
            for path in directory.glob("*.json"):
                payload = self._read_payload(path)
                source_refs = payload.get("source_refs")
                if isinstance(source_refs, list):
                    payload["source_refs"] = [
                        aliases.get(reference, reference)
                        for reference in source_refs
                    ]
                cross_refs = payload.get("cross_refs")
                if isinstance(cross_refs, list):
                    for reference in cross_refs:
                        if isinstance(reference, dict):
                            reference["ref"] = aliases.get(
                                reference.get("ref"),
                                reference.get("ref"),
                            )
                self._write_payload(path, payload)

    def write(self, entry: Entry) -> None:
        path = self._path_for(entry.id, entry.memory_class)
        tmp = path.with_suffix(".tmp")
        with self._lock:
            tmp.write_text(
                json.dumps(entry.as_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            tmp.replace(path)

    def _find_path(self, mem_id: str) -> Optional[Path]:
        self._validate_id(mem_id)
        # Canonical IDs take precedence over historical aliases. Raw remains
        # directly accessible through its migrated raw_* ID.
        for directory in self._class_directories.values():
            canonical = directory / f"{mem_id}.json"
            if canonical.is_file():
                return canonical
        mem_id = self._legacy_aliases.get(mem_id, mem_id)
        for directory in self._class_directories.values():
            candidate = directory / f"{mem_id}.json"
            if candidate.is_file():
                return candidate
        legacy_path = self._path_for(mem_id)
        return legacy_path if legacy_path.is_file() else None

    def read(self, mem_id: str) -> Optional[Entry]:
        requested_id = mem_id
        path = self._find_path(mem_id)
        if path is None:
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            entry = Entry.from_dict(data)
            expected_id = requested_id if path.stem == requested_id else self._legacy_aliases.get(requested_id, requested_id)
            if entry.id != expected_id:
                return None
            return entry
        except Exception:
            return None

    def exists(self, mem_id: str) -> bool:
        return self._find_path(mem_id) is not None

    def list_ids(self) -> List[str]:
        ids = set()
        for directory in self._class_directories.values():
            if directory.is_dir():
                ids.update(path.stem for path in directory.glob("*.json"))
        if self.entries_dir.is_dir():
            ids.update(
                path.stem
                for path in self.entries_dir.glob("mem_*.json")
                if path.stem not in self._legacy_aliases
            )
        return sorted(ids)

    def iter_entries(self) -> Iterator[Entry]:
        for mem_id in self.list_ids():
            entry = self.read(mem_id)
            if entry is not None:
                yield entry

    def count(self) -> int:
        return len(self.list_ids())
