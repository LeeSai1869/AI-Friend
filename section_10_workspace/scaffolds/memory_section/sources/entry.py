"""The Memory Entry - the standard unit of memory.

Every entry has the same shape. Three memory classes:
raw, tested, derived. State is computed from counts, not stored.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from . import config


@dataclass
class Originator:
    type: str
    name: str

    def as_dict(self) -> Dict[str, str]:
        return {"type": self.type, "name": self.name}


@dataclass
class Failure:
    ts: float
    reason: str
    code: str = "unknown"
    context_memory: Optional[str] = None
    chat: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CrossRef:
    ref: str
    reason: str

    def as_dict(self) -> Dict[str, str]:
        return {"ref": self.ref, "reason": self.reason}


@dataclass
class Entry:
    id: str
    ts: float

    domain_created: str
    memory_class: str = "raw"

    originator: List[Originator] = field(default_factory=list)

    kind: str = "fact"
    title: str = ""
    content: str = ""
    tags: List[str] = field(default_factory=list)

    writers: List[str] = field(default_factory=list)
    readers: List[str] = field(default_factory=list)

    success_count: int = 0
    failure_count: int = 0
    last_success_ts: Optional[float] = None
    last_failure_ts: Optional[float] = None
    failures: List[Failure] = field(default_factory=list)

    cross_refs: List[CrossRef] = field(default_factory=list)
    context_memory: Optional[str] = None
    active_chat: Optional[str] = None

    score: float = 0.0
    status: str = "active"

    superseded_by: Optional[str] = None
    supersedes: Optional[str] = None

    source_refs: List[str] = field(default_factory=list)
    derivation_note: str = ""
    derived_status: str = "active"

    def recompute_score(self) -> None:
        self.score = config.compute_score(self.success_count, self.failure_count)

    def state(self) -> str:
        return config.compute_state(self.success_count, self.failure_count)

    def record_success(self) -> None:
        self.success_count += 1
        self.last_success_ts = time.time()
        self.recompute_score()

    def record_failure(
        self,
        reason: str,
        code: str = "unknown",
        context_memory: Optional[str] = None,
        chat: Optional[str] = None,
    ) -> None:
        self.failures.append(Failure(
            ts=time.time(), reason=reason, code=code,
            context_memory=context_memory, chat=chat,
        ))
        self.failure_count += 1
        self.last_failure_ts = time.time()
        self.recompute_score()

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "ts": self.ts,
            "domain_created": self.domain_created,
            "memory_class": self.memory_class,
            "originator": [o.as_dict() for o in self.originator],
            "kind": self.kind,
            "title": self.title,
            "content": self.content,
            "tags": list(self.tags),
            "writers": list(self.writers),
            "readers": list(self.readers),
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_success_ts": self.last_success_ts,
            "last_failure_ts": self.last_failure_ts,
            "failures": [f.as_dict() for f in self.failures],
            "cross_refs": [c.as_dict() for c in self.cross_refs],
            "context_memory": self.context_memory,
            "active_chat": self.active_chat,
            "score": self.score,
            "status": self.status,
            "superseded_by": self.superseded_by,
            "supersedes": self.supersedes,
            "source_refs": list(self.source_refs),
            "derivation_note": self.derivation_note,
            "derived_status": self.derived_status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entry":
        return cls(
            id=data["id"],
            ts=data["ts"],
            domain_created=data["domain_created"],
            memory_class=data.get("memory_class", "raw"),
            originator=[Originator(**o) for o in data.get("originator", [])],
            kind=data.get("kind", "fact"),
            title=data.get("title", ""),
            content=data.get("content", ""),
            tags=list(data.get("tags", [])),
            writers=list(data.get("writers", [])),
            readers=list(data.get("readers", [])),
            success_count=int(data.get("success_count", 0)),
            failure_count=int(data.get("failure_count", 0)),
            last_success_ts=data.get("last_success_ts"),
            last_failure_ts=data.get("last_failure_ts"),
            failures=[Failure(**f) for f in data.get("failures", [])],
            cross_refs=[CrossRef(**c) for c in data.get("cross_refs", [])],
            context_memory=data.get("context_memory"),
            active_chat=data.get("active_chat"),
            score=float(data.get("score", 0.0)),
            status=data.get("status", "active"),
            superseded_by=data.get("superseded_by"),
            supersedes=data.get("supersedes"),
            source_refs=list(data.get("source_refs", [])),
            derivation_note=data.get("derivation_note", ""),
            derived_status=data.get("derived_status", "active"),
        )


def make_id(domain_prefix: str, sequence_number: int) -> str:
    if domain_prefix not in config.DOMAIN_PREFIXES:
        raise ValueError(f"unknown domain prefix: {domain_prefix}")
    seq = str(sequence_number).zfill(config.SEQUENCE_DIGITS)
    return f"{config.ID_PREFIX}_{domain_prefix}_{seq}"


def parse_id(mem_id: str) -> Dict[str, str]:
    parts = mem_id.split("_")
    if len(parts) != 3 or parts[0] != config.ID_PREFIX:
        raise ValueError(f"malformed memory id: {mem_id}")
    return {"prefix": parts[0], "domain": parts[1], "sequence": parts[2]}
