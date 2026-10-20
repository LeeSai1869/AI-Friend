"""The index - fast lookup by id, tag, class, domain, status."""
from __future__ import annotations

from typing import Dict, List, Set

from .store import Store


class Index:

    def __init__(self, store: Store):
        self.store = store
        self._by_domain: Dict[str, Set[str]] = {}
        self._by_tag: Dict[str, Set[str]] = {}
        self._by_kind: Dict[str, Set[str]] = {}
        self._by_class: Dict[str, Set[str]] = {}
        self._by_status: Dict[str, Set[str]] = {}
        self._built = False

    def build(self) -> None:
        self._by_domain.clear()
        self._by_tag.clear()
        self._by_kind.clear()
        self._by_class.clear()
        self._by_status.clear()
        for entry in self.store.iter_entries():
            self._add(entry)
        self._built = True

    def _add(self, entry) -> None:
        self._by_domain.setdefault(entry.domain_created, set()).add(entry.id)
        self._by_kind.setdefault(entry.kind, set()).add(entry.id)
        self._by_class.setdefault(entry.memory_class, set()).add(entry.id)
        self._by_status.setdefault(entry.status, set()).add(entry.id)
        for tag in entry.tags:
            self._by_tag.setdefault(tag.lower(), set()).add(entry.id)

    def _ensure(self) -> None:
        if not self._built:
            self.build()

    def by_domain(self, domain: str) -> List[str]:
        self._ensure()
        return sorted(self._by_domain.get(domain, set()))

    def by_tag(self, tag: str) -> List[str]:
        self._ensure()
        return sorted(self._by_tag.get(tag.lower(), set()))

    def by_kind(self, kind: str) -> List[str]:
        self._ensure()
        return sorted(self._by_kind.get(kind, set()))

    def by_class(self, memory_class: str) -> List[str]:
        self._ensure()
        return sorted(self._by_class.get(memory_class, set()))

    def by_status(self, status: str) -> List[str]:
        self._ensure()
        return sorted(self._by_status.get(status, set()))

    def add_entry(self, entry) -> None:
        if not self._built:
            return
        self._add(entry)
