"""The Memory API.

Three memory classes: raw, tested, derived.
State is computed from counts, not stored.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import config
from .entry import Entry, Originator, Failure, CrossRef, make_id, make_raw_id, parse_id
from .store import Store
from .index import Index


class Memory:

    def __init__(self, root: Path = None):
        memory_root = Path(root) if root else config.MEMORY_ROOT
        self.store = Store(memory_root)
        self.index = Index(self.store)
        self._seq_file = memory_root / "_sequences.json"
        self._sequences = self._load_sequences()

    def _load_sequences(self) -> Dict[str, int]:
        sequences = {}
        if self._seq_file.exists():
            try:
                payload = json.loads(self._seq_file.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    sequences = {
                        str(domain): int(value)
                        for domain, value in payload.items()
                    }
            except Exception:
                sequences = {}
        for mem_id in self.store.list_ids():
            match = re.fullmatch(r"mem_([A-Za-z]+)_(\d+)", mem_id)
            if match and match.group(1) in config.DOMAIN_PREFIXES:
                domain, sequence = match.groups()
                sequences[domain] = max(
                    sequences.get(domain, 0),
                    int(sequence),
                )
        return sequences

    def _save_sequences(self) -> None:
        self._seq_file.write_text(json.dumps(self._sequences, indent=2), encoding="utf-8")

    def _next_seq(self, domain_prefix: str) -> int:
        current = self._sequences.get(domain_prefix, 0)
        nxt = current + 1
        # Historical numbered Raw IDs are compatibility references, not the
        # mainstream sequence's high-water mark. Skip individual collisions
        # without importing their numbers into Tested/Derived numbering.
        while make_id(domain_prefix, nxt) in self.store._legacy_aliases:
            nxt += 1
        self._sequences[domain_prefix] = nxt
        self._save_sequences()
        return nxt

    def _new_raw_id(self, title: str) -> str:
        while True:
            mem_id = make_raw_id(title)
            if not self.store.exists(mem_id):
                return mem_id

    def record(self, *args, **kwargs) -> Entry:
        from .locking import memory_lock
        with memory_lock(self.store.memory_root, '.entry-write.lock'):
            self._sequences = self._load_sequences()
            return self._record(*args, **kwargs)

    def _record(
        self,
        domain: str,
        kind: str,
        title: str,
        content: str,
        memory_class: str = "raw",
        originator: Optional[List[Dict[str, str]]] = None,
        tags: Optional[List[str]] = None,
        writers: Optional[List[str]] = None,
        readers: Optional[List[str]] = None,
        context_memory: Optional[str] = None,
        active_chat: Optional[str] = None,
        cross_refs: Optional[List[Dict[str, str]]] = None,
        source_refs: Optional[List[str]] = None,
        derivation_note: str = "",
        source: Optional[Dict[str, Any]] = None,
    ) -> Entry:
        if domain not in config.DOMAIN_PREFIXES:
            raise ValueError(f"unknown domain prefix: {domain}")
        if kind not in config.VALID_KINDS:
            raise ValueError(f"unknown kind: {kind}")
        if memory_class not in config.VALID_MEMORY_CLASSES:
            raise ValueError(f"unknown memory_class: {memory_class}")

        if memory_class == "raw":
            mem_id = self._new_raw_id(title)
        else:
            seq = self._next_seq(domain)
            mem_id = make_id(domain, seq)

        orig = [Originator(type=o.get("type", "unknown"), name=o.get("name", "unknown"))
                for o in (originator or [])]
        refs = [CrossRef(ref=c["ref"], reason=c.get("reason", "used_by"))
                for c in (cross_refs or [])]

        entry = Entry(
            id=mem_id, ts=time.time(),
            domain_created=domain, memory_class=memory_class,
            originator=orig, kind=kind, title=title, content=content,
            tags=list(tags or []),
            writers=list(writers or [domain]),
            readers=list(readers or [domain]),
            cross_refs=refs,
            context_memory=context_memory,
            active_chat=active_chat,
            source_refs=list(source_refs or []),
            derivation_note=derivation_note,
            source=source or {},
        )
        entry.recompute_score()
        self.store.write(entry)
        self.index.add_entry(entry)
        return entry

    def get(self, mem_id: str) -> Optional[Entry]:
        return self.store.read(mem_id)

    def exists(self, mem_id: str) -> bool:
        return self.store.exists(mem_id)

    def count(self) -> int:
        return self.store.count()

    def get_state(self, mem_id: str) -> Optional[str]:
        entry = self.store.read(mem_id)
        if entry is None:
            return None
        return entry.state()

    def search(
        self,
        query: str = "",
        domain: Optional[str] = None,
        kind: Optional[str] = None,
        tag: Optional[str] = None,
        memory_class: Optional[str] = None,
        status: str = "active",
        state: Optional[str] = None,
        limit: int = 50,
    ) -> List[Entry]:
        # Build from disk for each query: other authenticated sessions may
        # have appended entries since this Memory instance built its index.
        index = Index(self.store)
        candidates = None

        if domain:
            candidates = set(index.by_domain(domain))
        if tag:
            tag_set = set(index.by_tag(tag))
            candidates = tag_set if candidates is None else candidates & tag_set
        if kind:
            kind_set = set(index.by_kind(kind))
            candidates = kind_set if candidates is None else candidates & kind_set
        if memory_class:
            class_set = set(index.by_class(memory_class))
            candidates = class_set if candidates is None else candidates & class_set
        if status:
            status_set = set(index.by_status(status))
            candidates = status_set if candidates is None else candidates & status_set

        if candidates is None:
            candidates = set(self.store.list_ids())

        entries = []
        for mem_id in candidates:
            entry = self.store.read(mem_id)
            if entry is None:
                continue
            if state and entry.state() != state:
                continue
            if query:
                q = query.lower()
                text = (entry.title + " " + entry.content + " " + " ".join(entry.tags)).lower()
                if q not in text:
                    continue
            entries.append(entry)

        entries.sort(key=lambda e: e.score, reverse=True)
        return entries[:limit]

    def record_success(self, mem_id: str) -> Optional[Entry]:
        entry = self.store.read(mem_id)
        if entry is None:
            return None
        entry.record_success()
        self.store.write(entry)
        return entry

    def record_failure(self, mem_id: str, reason: str, code: str = "unknown",
                       context_memory: Optional[str] = None,
                       chat: Optional[str] = None) -> Optional[Entry]:
        entry = self.store.read(mem_id)
        if entry is None:
            return None
        entry.record_failure(reason=reason, code=code,
                             context_memory=context_memory, chat=chat)
        self.store.write(entry)
        return entry

    def add_cross_ref(self, mem_id: str, ref: str, reason: str = "used_by") -> Optional[Entry]:
        entry = self.store.read(mem_id)
        if entry is None:
            return None
        for existing in entry.cross_refs:
            if existing.ref == ref and existing.reason == reason:
                return entry
        entry.cross_refs.append(CrossRef(ref=ref, reason=reason))
        self.store.write(entry)
        return entry

    def add_writer(self, mem_id: str, domain: str) -> Optional[Entry]:
        entry = self.store.read(mem_id)
        if entry is None:
            return None
        if domain not in entry.writers:
            entry.writers.append(domain)
            self.store.write(entry)
        return entry

    def add_reader(self, mem_id: str, domain: str) -> Optional[Entry]:
        entry = self.store.read(mem_id)
        if entry is None:
            return None
        if domain not in entry.readers:
            entry.readers.append(domain)
            self.store.write(entry)
        return entry

    def retire(self, mem_id: str) -> Optional[Entry]:
        entry = self.store.read(mem_id)
        if entry is None:
            return None
        entry.status = "retired"
        self.store.write(entry)
        self.index.build()
        return entry

    def supersede(self, old_id: str, new_id: str) -> Optional[Entry]:
        old = self.store.read(old_id)
        new = self.store.read(new_id)
        if old is None or new is None:
            return None
        old.status = "superseded"
        old.superseded_by = new_id
        new.supersedes = old_id
        self.store.write(old)
        self.store.write(new)
        self.index.build()
        return old

    def mark_derived_contested(self, mem_id: str) -> Optional[Entry]:
        entry = self.store.read(mem_id)
        if entry is None:
            return None
        if entry.memory_class != "derived":
            return entry
        entry.derived_status = "contested"
        self.store.write(entry)
        return entry

    def mark_derived_obsolete(self, mem_id: str) -> Optional[Entry]:
        entry = self.store.read(mem_id)
        if entry is None:
            return None
        if entry.memory_class != "derived":
            return entry
        entry.derived_status = "obsolete"
        self.store.write(entry)
        return entry

    def summary(self) -> Dict[str, Any]:
        total = 0
        by_domain: Dict[str, int] = {}
        by_class: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        by_state: Dict[str, int] = {}
        verified = 0
        for entry in self.store.iter_entries():
            total += 1
            by_domain[entry.domain_created] = by_domain.get(entry.domain_created, 0) + 1
            by_class[entry.memory_class] = by_class.get(entry.memory_class, 0) + 1
            by_status[entry.status] = by_status.get(entry.status, 0) + 1
            st = entry.state()
            by_state[st] = by_state.get(st, 0) + 1
            if st == "verified":
                verified += 1
        return {
            "total": total,
            "verified": verified,
            "by_domain": by_domain,
            "by_class": by_class,
            "by_status": by_status,
            "by_state": by_state,
        }
