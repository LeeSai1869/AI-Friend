"""The Memory Bridge.

A thin interface between the mind and the memory store.

Four write operations and several read operations.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .api import Memory


class MemoryBridge:

    def __init__(self, memory: Memory):
        self.memory = memory

    # ----------------------------------------------------------------
    # READ
    # ----------------------------------------------------------------

    def recall(
        self,
        query: str,
        memory_class: Optional[str] = None,
        domain: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        entries = self.memory.search(
            query=query,
            domain=domain,
            memory_class=memory_class,
            limit=limit,
        )
        if tags:
            tag_set = set(t.lower() for t in tags)
            entries = [
                e for e in entries
                if tag_set & set(t.lower() for t in e.tags)
            ]
        return [self._summarize(e) for e in entries]

    def recall_tested(
        self,
        query: str,
        domain: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        return self.recall(
            query=query,
            memory_class="tested",
            domain=domain,
            limit=limit,
        )

    def recall_rejections(
        self,
        query: str,
        domain: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        entries = self.memory.search(
            query=query,
            domain=domain,
            memory_class="tested",
            state="rejected",
            limit=limit,
        )
        return [self._summarize(e) for e in entries]

    def get(self, mem_id: str) -> Optional[Dict[str, Any]]:
        entry = self.memory.get(mem_id)
        if entry is None:
            return None
        return entry.as_dict()

    # ----------------------------------------------------------------
    # WRITE
    # ----------------------------------------------------------------

    def remember_raw(
        self,
        domain: str,
        title: str,
        content: str,
        originator: Optional[List[Dict[str, str]]] = None,
        tags: Optional[List[str]] = None,
        kind: str = "fact",
        source: Optional[Dict[str, Any]] = None,
    ) -> str:
        entry = self.memory.record(
            domain=domain,
            kind=kind,
            title=title,
            content=content,
            memory_class="raw",
            source=source,
            originator=originator,
            tags=tags,
        )
        return entry.id

    def remember_tested(
        self,
        domain: str,
        title: str,
        content: str,
        originator: Optional[List[Dict[str, str]]] = None,
        tags: Optional[List[str]] = None,
        kind: str = "fact",
        success: bool = True,
        reason: str = "",
        failure_code: str = "unknown",
        source_refs: Optional[List[str]] = None,
        source: Optional[Dict[str, Any]] = None,
    ) -> str:
        entry = self.memory.record(
            domain=domain,
            kind=kind,
            title=title,
            content=content,
            memory_class="tested",
            source=source,
            originator=originator,
            tags=tags,
            source_refs=source_refs or [],
        )
        if success:
            self.memory.record_success(entry.id)
        else:
            self.memory.record_failure(
                entry.id,
                reason=reason or "test failed",
                code=failure_code,
            )
        return entry.id

    def remember_derived(
        self,
        domain: str,
        title: str,
        content: str,
        source_refs: List[str],
        originator: Optional[List[Dict[str, str]]] = None,
        tags: Optional[List[str]] = None,
        kind: str = "theory",
        derivation_note: str = "",
        source: Optional[Dict[str, Any]] = None,
    ) -> str:
        entry = self.memory.record(
            domain=domain,
            kind=kind,
            title=title,
            content=content,
            memory_class="derived",
            originator=originator,
            tags=tags,
            source_refs=source_refs,
            derivation_note=derivation_note,
            source=source,
        )
        return entry.id

    # ----------------------------------------------------------------
    # UPDATE
    # ----------------------------------------------------------------

    def confirm_success(self, mem_id: str) -> bool:
        return self.memory.record_success(mem_id) is not None

    def confirm_failure(self, mem_id: str, reason: str,
                        code: str = "unknown") -> bool:
        return self.memory.record_failure(
            mem_id, reason=reason, code=code
        ) is not None

    # ----------------------------------------------------------------
    # SUMMARY
    # ----------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        return self.memory.summary()


    def source_scores(self, domain: str, capability: str) -> Dict[str, int]:
        """Count successful uses per model for a domain + capability.

        Used by the roster reordering logic in the mind.

        A tested entry with a source tag is a success record. Pure
        failures (failure_count > 0, success_count == 0) are
        excluded from the count.
        """
        counts: Dict[str, int] = {}
        for entry in self.memory.store.iter_entries():
            src = getattr(entry, "source", None) or {}
            if src.get("type") != "model":
                continue
            if src.get("organ") != domain:
                continue
            if src.get("capability") != capability:
                continue
            if entry.memory_class != "tested":
                continue
            if entry.failure_count > 0 and entry.success_count == 0:
                continue
            name = src.get("name", "")
            counts[name] = counts.get(name, 0) + 1
        return counts

    def _summarize(self, entry) -> Dict[str, Any]:
        return {
            "id": entry.id,
            "memory_class": entry.memory_class,
            "domain": entry.domain_created,
            "kind": entry.kind,
            "title": entry.title,
            "content": entry.content[:500],
            "tags": list(entry.tags),
            "state": entry.state(),
            "score": entry.score,
            "success_count": entry.success_count,
            "failure_count": entry.failure_count,
            "source_refs": list(entry.source_refs),
        }
