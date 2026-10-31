"""Shared Memory Service.

All callers use controlled clients rather than receiving the Memory
backend or its Store directly. Domain labels organize knowledge; they
do not, by themselves, restrict cross-domain learning.

This is an in-process interface boundary, not an OS security sandbox.
"""
from __future__ import annotations

import copy
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import config
from .api import Memory
from .bridge import MemoryBridge


def serialized_knowledge(method):
    from functools import wraps
    @wraps(method)
    def call(self, *args, **kwargs):
        from .locking import memory_lock
        with memory_lock(self._bridge.memory.store.memory_root, '.knowledge-write.lock'):
            self._load_knowledge_journal()
            return method(self, *args, **kwargs)
    return call


class MemoryService:
    """Central entry point for memory operations."""

    def __init__(self, memory: Memory):
        self._bridge = MemoryBridge(memory)
        self._pending_deletions: List[Dict[str, Any]] = []
        self._next_proposal_id = 1
        self._pending_knowledge: List[Dict[str, Any]] = []
        self._next_knowledge_proposal_id = 1
        self._proposal_handler = None

        entries_dir = Path(self._bridge.memory.store.entries_dir)
        self._knowledge_journal = entries_dir.parent / "knowledge_proposals.json"
        self._deletion_journal = entries_dir.parent / "deletion_proposals.json"
        self._load_knowledge_journal()
        self._load_deletion_journal()
        from .processing import ProcessingJournal
        self.processing = ProcessingJournal(self._bridge.memory.store.memory_root)
        self.recover_raw_intakes()

    def _load_deletion_journal(self) -> None:
        """Load deletion requests; never silently discard a corrupt journal."""
        path = self._deletion_journal
        if not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("version") != 1:
                raise ValueError("unsupported journal format")
            proposals = payload.get("proposals")
            next_id = payload.get("next_proposal_id")
            if not isinstance(proposals, list):
                raise ValueError("proposals must be a list")
            if type(next_id) is not int or next_id < 1:
                raise ValueError("invalid next proposal ID")
            seen = set()
            for item in proposals:
                if not isinstance(item, dict):
                    raise ValueError("proposal must be an object")
                pid = item.get("proposal_id")
                if type(pid) is not int or pid < 1 or pid in seen:
                    raise ValueError("invalid or duplicate proposal ID")
                if item.get("status") not in {"pending", "approved", "rejected"}:
                    raise ValueError("invalid proposal status")
                if not isinstance(item.get("memory_id"), str):
                    raise ValueError("invalid memory ID")
                if not isinstance(item.get("reason"), str) or not item["reason"].strip():
                    raise ValueError("invalid proposal reason")
                seen.add(pid)
            if seen and next_id <= max(seen):
                raise ValueError("next proposal ID would reuse an existing ID")
            self._pending_deletions = proposals
            self._next_proposal_id = next_id
        except Exception as exc:
            raise RuntimeError(
                f"Cannot safely load deletion proposal journal at {path}: {exc}"
            ) from exc

    def _save_deletion_journal(self) -> None:
        """Atomically save the full deletion-request history."""
        path = self._deletion_journal
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "next_proposal_id": self._next_proposal_id,
            "proposals": self._pending_deletions,
        }
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent,
                prefix=path.name + ".", suffix=".tmp", delete=False
            ) as handle:
                temp_name = handle.name
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)

    def _load_knowledge_journal(self) -> None:
        """Restore the complete proposal history; never silently discard corruption."""
        path = self._knowledge_journal
        if not path.exists():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or payload.get("version") != 1:
                raise ValueError("unsupported journal format")
            proposals = payload.get("proposals")
            next_id = payload.get("next_knowledge_proposal_id")
            if not isinstance(proposals, list):
                raise ValueError("proposals must be a list")
            if type(next_id) is not int or next_id < 1:
                raise ValueError("invalid next proposal ID")

            seen = set()
            valid_statuses = {"pending", "approved", "rejected"}
            for item in proposals:
                if not isinstance(item, dict):
                    raise ValueError("proposal entry must be an object")
                pid = item.get("proposal_id")
                if type(pid) is not int or pid < 1 or pid in seen:
                    raise ValueError("invalid or duplicate proposal ID")
                if item.get("status") not in valid_statuses:
                    raise ValueError("invalid proposal status")
                seen.add(pid)
            if seen and next_id <= max(seen):
                raise ValueError("next proposal ID would reuse an existing ID")

            self._pending_knowledge = proposals
            self._next_knowledge_proposal_id = next_id
        except Exception as exc:
            raise RuntimeError(
                f"Cannot safely load knowledge proposal journal at {path}: {exc}"
            ) from exc

    def _save_knowledge_journal(self) -> None:
        """Atomically replace the journal so a partial JSON file is not exposed."""
        path = self._knowledge_journal
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "next_knowledge_proposal_id": self._next_knowledge_proposal_id,
            "proposals": self._pending_knowledge,
        }
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=path.name + ".",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_name = handle.name
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)

    def _find_committed_entry(self, proposal_id: int):
        """Find an entry already committed for this proposal, if any."""
        for entry in self._bridge.memory.store.iter_entries():
            source = getattr(entry, "source", None)
            provenance = source.get("memory_proposal") if isinstance(source, dict) else None
            if isinstance(provenance, dict) and provenance.get("proposal_id") == proposal_id:
                return entry
        return None

    def register_proposal_handler(self, handler) -> None:
        """Register Central Mind's handler for submitted knowledge proposals."""
        if not callable(handler):
            raise TypeError("proposal handler must be callable")
        self._proposal_handler = handler

    def _dispatch_knowledge_proposal(
        self, proposal: Dict[str, Any]
    ) -> Dict[str, Any]:
        handler = self._proposal_handler
        if handler is None:
            return dict(proposal)

        result = handler(dict(proposal))
        if not isinstance(result, dict):
            raise TypeError("proposal handler must return a dictionary")
        return result

    def client(self, actor: str, role: str, domain: str) -> "MemoryClient":
        if not isinstance(actor, str) or not actor.strip():
            raise ValueError("actor must be a non-empty string")
        if not isinstance(role, str) or not role.strip():
            raise ValueError("role must be a non-empty string")
        if domain not in config.DOMAIN_PREFIXES:
            raise ValueError(f"unknown domain prefix: {domain}")
        return MemoryClient(self, actor.strip(), role.strip(), domain)

    def _record_trainer_intake(
        self,
        *,
        actor: str,
        role: str,
        domain: str,
        kind: str,
        title: str,
        content: str,
        tags: List[str],
        source_refs: List[str],
        source: Dict[str, Any],
    ) -> str:
        if role != "trainer":
            raise PermissionError("Trainer role required for Raw Memory intake")
        if domain not in config.DOMAIN_PREFIXES:
            raise ValueError(f"unknown domain prefix: {domain}")
        if kind not in config.VALID_KINDS:
            raise ValueError(f"unknown memory kind: {kind}")
        if not title.strip() or not content.strip():
            raise ValueError("intake title and content must be non-empty")

        entry = self._bridge.memory.record(
            domain=domain,
            kind=kind,
            title=title.strip(),
            content=content,
            memory_class="raw",
            originator=[{"type": role, "name": actor}],
            tags=tags,
            writers=[role],
            readers=["central_mind"],
            source_refs=source_refs,
            source=source,
            derivation_note=(
                "Trainer-introduced material. Raw and unverified; "
                "Central Mind may recall it for analysis and testing."
            ),
        )
        try:
            self.enqueue_raw(entry.id)
        except Exception as exc:
            # Storage succeeded. Queue recovery can discover this source later.
            self._processing_queue_error = str(exc)
        return entry.id

    def enqueue_raw(self, raw_id):
        import hashlib
        entry = self._bridge.memory.get(raw_id)
        if entry is None or entry.memory_class != 'raw':
            raise ValueError('Only an existing Raw entry can be examined')
        return self.processing.enqueue(entry.id, entry.domain_created, hashlib.sha256(entry.content.encode()).hexdigest())

    def recover_raw_intakes(self):
        for entry in self._bridge.memory.store.iter_entries():
            if entry.memory_class == 'raw':
                self.enqueue_raw(entry.id)

    def compare_raw_source(self, source):
        matches=[]
        for entry in self._bridge.memory.store.iter_entries():
            if entry.id != source['id'] and entry.memory_class == 'raw' and entry.domain_created == source['domain_created'] and entry.content == source['content']:
                matches.append(entry.id)
        return {'status':'duplicate' if matches else 'new','raw_ids':matches}

    def examination_context(self, domain, limit=16):
        rows=[]
        for entry in self._bridge.memory.store.iter_entries():
            if entry.domain_created == domain and entry.memory_class != 'raw' and entry.status == 'active':
                rows.append({'id':entry.id, 'kind':entry.kind, 'title':entry.title,
                             'content':entry.content[:16000], 'source':dict(entry.source),
                             'truncated':len(entry.content)>16000})
                if len(rows)>=limit:
                    break
        return rows

    def reconcile_candidate(self, candidate):
        # Called by Mind; domains receive only the resulting comparison facts.
        content = candidate.get('content', '').strip()
        domain = candidate.get('domain')
        key = (candidate.get('source') or {}).get('semantic_key')
        conflicts = []
        for entry in self._bridge.memory.store.iter_entries():
            if entry.status != 'active' or entry.domain_created != domain or entry.memory_class == 'raw':
                continue
            if entry.kind == candidate.get('kind') and entry.content.strip() == content:
                return {'status':'duplicate','memory_ids':[entry.id]}
            if key and entry.source.get('semantic_key') == key:
                conflicts.append(entry.id)
        return {'status':'conflicting' if conflicts else 'new','memory_ids':conflicts}

    def _propose_delete(
        self, actor: str, mem_id: str, reason: str
    ) -> Dict[str, Any]:
        if not self._bridge.memory.exists(mem_id):
            raise ValueError(f"memory entry does not exist: {mem_id}")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("a non-empty reason is required")

        proposal = {
            "proposal_id": self._next_proposal_id,
            "status": "pending",
            "memory_id": mem_id,
            "proposed_by": actor,
            "reason": reason.strip(),
            "created_at": time.time(),
        }
        self._next_proposal_id += 1
        self._pending_deletions.append(proposal)
        try:
            self._save_deletion_journal()
        except Exception:
            self._pending_deletions.pop()
            self._next_proposal_id -= 1
            raise
        return copy.deepcopy(proposal)

    def pending_deletion_proposals(self) -> List[Dict[str, Any]]:
        """Return copies of pending requests without deleting memory."""
        return [
            copy.deepcopy(item)
            for item in self._pending_deletions
            if item["status"] == "pending"
        ]

    @serialized_knowledge
    def _propose_knowledge(
        self,
        actor: str,
        client_domain: str,
        *,
        title: str,
        content: str,
        domain: Optional[str] = None,
        kind: str = "fact",
        requested_class: str = "raw",
        originator: Optional[List[Dict[str, str]]] = None,
        tags: Optional[List[str]] = None,
        source_refs: Optional[List[str]] = None,
        source: Optional[Dict[str, Any]] = None,
        evidence: Optional[Any] = None,
        derivation_note: str = "",
    ) -> Dict[str, Any]:
        """Queue a knowledge proposal without creating or modifying memory."""
        if not isinstance(title, str) or not title.strip():
            raise ValueError("proposal title must be a non-empty string")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("proposal content must be a non-empty string")

        target_domain = domain or client_domain
        if target_domain not in config.DOMAIN_PREFIXES:
            raise ValueError(f"unknown domain prefix: {target_domain}")
        if kind not in config.VALID_KINDS:
            raise ValueError(f"unknown memory kind: {kind}")
        if requested_class not in config.VALID_MEMORY_CLASSES:
            raise ValueError(f"unknown requested memory class: {requested_class}")

        proposal = {
            "proposal_id": self._next_knowledge_proposal_id,
            "status": "pending",
            "proposed_by": actor,
            "domain": target_domain,
            "title": title.strip(),
            "content": content.strip(),
            "kind": kind,
            "requested_class": requested_class,
            "originator": list(originator or []),
            "tags": list(tags or []),
            "source_refs": list(source_refs or []),
            "source": dict(source) if source is not None else None,
            "evidence": evidence,
            "derivation_note": derivation_note.strip()
            if isinstance(derivation_note, str) else "",
            "created_at": time.time(),
            "decision": None,
            "memory_id": None,
        }
        # Persist before reporting submission as successful. Roll back the
        # in-memory queue and ID if serialization or disk writing fails.
        self._next_knowledge_proposal_id += 1
        self._pending_knowledge.append(proposal)
        try:
            self._save_knowledge_journal()
        except Exception:
            self._pending_knowledge.pop()
            self._next_knowledge_proposal_id -= 1
            raise
        return copy.deepcopy(proposal)

    def pending_knowledge_proposals(self) -> List[Dict[str, Any]]:
        """Return copies of pending proposals for Central Mind's review."""
        return [
            copy.deepcopy(proposal)
            for proposal in self._pending_knowledge
            if proposal["status"] == "pending"
        ]


    def _find_knowledge_proposal(self, proposal_id: int) -> Dict[str, Any]:
        for proposal in self._pending_knowledge:
            if proposal["proposal_id"] == proposal_id:
                return proposal
        raise KeyError(f"unknown knowledge proposal: {proposal_id}")

    def knowledge_proposal(self, proposal_id: int) -> Dict[str, Any]:
        """Return a copy of one proposal without exposing mutable service state."""
        return copy.deepcopy(self._find_knowledge_proposal(proposal_id))

    @serialized_knowledge
    def commit_approved_proposal(
        self,
        proposal_id: int,
        *,
        approved_by: str,
        decision_reason: str,
        approved_class: str,
    ) -> Dict[str, Any]:
        """Commit a pending proposal after an explicit Central Mind decision."""
        if approved_by != "central_mind":
            raise PermissionError("only Central Mind may approve knowledge")
        if not isinstance(decision_reason, str) or not decision_reason.strip():
            raise ValueError("approval reason must be non-empty")
        if approved_class not in config.VALID_MEMORY_CLASSES:
            raise ValueError(f"unknown approved memory class: {approved_class}")
        if approved_class == "raw":
            raise PermissionError(
                "Raw Memory is reserved for authenticated Trainer Intake; "
                "Central Mind proposal approval cannot create Raw Memory"
            )

        proposal = self._find_knowledge_proposal(proposal_id)
        if proposal["status"] != "pending":
            raise ValueError(
                f"proposal {proposal_id} is already {proposal['status']}"
            )

        source_payload = dict(proposal.get("source") or {})
        source_payload["memory_proposal"] = {
            "proposal_id": proposal["proposal_id"],
            "proposed_by": proposal["proposed_by"],
            "evidence": proposal.get("evidence"),
            "requested_class": proposal["requested_class"],
            "approved_class": approved_class,
            "decision_reason": decision_reason.strip(),
            "approved_by": approved_by,
        }

        if source_payload.get("intake_examiner_version"):
            comparison = self.reconcile_candidate(proposal)
            if comparison["status"] == "conflicting":
                raise ValueError("Candidate conflicts with existing knowledge; review is required")
            if comparison["status"] == "duplicate":
                proposal.update({"status": "approved", "decision": "approved", "decided_by": approved_by,
                    "decided_at": time.time(), "decision_reason": "Reused an identical existing knowledge entry",
                    "approved_class": approved_class, "memory_id": comparison["memory_ids"][0], "reused_existing": True})
                self._save_knowledge_journal()
                return copy.deepcopy(proposal)

        # Recover a prior commit if the process stopped after writing the
        # entry but before persisting the proposal's approved status.
        existing = self._find_committed_entry(proposal_id)
        if existing is not None:
            snapshot = copy.deepcopy(proposal)
            provenance = existing.source.get("memory_proposal", {})
            proposal.update({
                "status": "approved",
                "decision": "approved",
                "decided_by": provenance.get("approved_by", approved_by),
                "decided_at": time.time(),
                "decision_reason": provenance.get(
                    "decision_reason", decision_reason.strip()
                ),
                "approved_class": provenance.get("approved_class", approved_class),
                "memory_id": existing.id,
            })
            try:
                self._save_knowledge_journal()
            except Exception:
                proposal.clear()
                proposal.update(snapshot)
                raise
            return copy.deepcopy(proposal)

        # Write the memory entry first. If the journal update later fails,
        # the provenance lookup above prevents a duplicate on retry.
        entry = self._bridge.memory.record(
            domain=proposal["domain"],
            kind=proposal["kind"],
            title=proposal["title"],
            content=proposal["content"],
            memory_class=approved_class,
            originator=proposal["originator"],
            tags=proposal["tags"],
            source_refs=proposal["source_refs"],
            source=source_payload,
            derivation_note=proposal["derivation_note"],
        )

        snapshot = copy.deepcopy(proposal)
        proposal["status"] = "approved"
        proposal["decision"] = "approved"
        proposal["decided_by"] = approved_by
        proposal["decided_at"] = time.time()
        proposal["decision_reason"] = decision_reason.strip()
        proposal["approved_class"] = approved_class
        proposal["memory_id"] = entry.id
        try:
            self._save_knowledge_journal()
        except Exception:
            proposal.clear()
            proposal.update(snapshot)
            raise
        return copy.deepcopy(proposal)

    @serialized_knowledge
    def reject_knowledge_proposal(
        self,
        proposal_id: int,
        *,
        decided_by: str,
        decision_reason: str,
    ) -> Dict[str, Any]:
        """Reject a pending proposal without writing a memory entry."""
        if decided_by != "central_mind":
            raise PermissionError("only Central Mind may reject knowledge")
        if not isinstance(decision_reason, str) or not decision_reason.strip():
            raise ValueError("rejection reason must be non-empty")

        proposal = self._find_knowledge_proposal(proposal_id)
        if proposal["status"] != "pending":
            raise ValueError(
                f"proposal {proposal_id} is already {proposal['status']}"
            )

        snapshot = copy.deepcopy(proposal)
        proposal["status"] = "rejected"
        proposal["decision"] = "rejected"
        proposal["decided_by"] = decided_by
        proposal["decided_at"] = time.time()
        proposal["decision_reason"] = decision_reason.strip()
        try:
            self._save_knowledge_journal()
        except Exception:
            proposal.clear()
            proposal.update(snapshot)
            raise
        return copy.deepcopy(proposal)


class MemoryClient:
    """Approved common interface presented to a memory-service caller."""

    def __init__(
        self, service: MemoryService, actor: str, role: str, domain: str
    ):
        self._service = service
        self.actor = actor
        self.role = role
        self.domain = domain

    # READ

    def recall(
        self,
        query: str,
        memory_class: Optional[str] = None,
        domain: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        if self.role != "central_mind" and memory_class == "raw":
            return []
        if self.role != "central_mind" and memory_class is None:
            # Filter classes before limiting, so inaccessible Raw records cannot
            # crowd approved knowledge out of a domain's recall window.
            entries = []
            for allowed_class in ("tested", "derived"):
                entries.extend(self._service._bridge.recall(query=query, memory_class=allowed_class,
                               domain=domain, tags=tags, limit=limit))
            return sorted(entries, key=lambda item: (-item.get("score", 0), item["id"]))[:limit]
        entries = self._service._bridge.recall(
            query=query,
            memory_class=memory_class,
            domain=domain,
            tags=tags,
            limit=limit,
        )
        if self.role != "central_mind":
            entries = [
                entry
                for entry in entries
                if entry.get("memory_class") != "raw"
            ]
        return entries

    def recall_tested(
        self, query: str, domain: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        return self._service._bridge.recall_tested(
            query=query, domain=domain, limit=limit
        )

    def recall_rejections(
        self, query: str, domain: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        return self._service._bridge.recall_rejections(
            query=query, domain=domain, limit=limit
        )

    def get(self, mem_id: str) -> Optional[Dict[str, Any]]:
        entry = self._service._bridge.get(mem_id)
        if (
            entry is not None
            and entry.get("memory_class") == "raw"
            and self.role != "central_mind"
        ):
            return None
        return entry

    def record_trainer_intake(
        self,
        *,
        domain: Optional[str] = None,
        kind: str,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        source_refs: Optional[List[str]] = None,
        source: Optional[Dict[str, Any]] = None,
    ) -> str:
        return self._service._record_trainer_intake(
            actor=self.actor,
            role=self.role,
            domain=domain or self.domain,
            kind=kind,
            title=title,
            content=content,
            tags=list(tags or []),
            source_refs=list(source_refs or []),
            source=dict(source or {}),
        )

    # PROPOSE KNOWLEDGE
    # Submission queues a proposal; it does not create or modify a memory entry.

    def propose_knowledge(
        self,
        title: str,
        content: str,
        domain: Optional[str] = None,
        kind: str = "fact",
        requested_class: str = "raw",
        originator: Optional[List[Dict[str, str]]] = None,
        tags: Optional[List[str]] = None,
        source_refs: Optional[List[str]] = None,
        source: Optional[Dict[str, Any]] = None,
        evidence: Optional[Any] = None,
        derivation_note: str = "",
    ) -> Dict[str, Any]:
        proposal = self._service._propose_knowledge(
            self.actor,
            self.domain,
            title=title,
            content=content,
            domain=domain,
            kind=kind,
            requested_class=requested_class,
            originator=originator,
            tags=tags,
            source_refs=source_refs,
            source=source,
            evidence=evidence,
            derivation_note=derivation_note,
        )
        return self._service._dispatch_knowledge_proposal(proposal)

    # Deletion is proposal-only; domains cannot mutate stored entries.

    def propose_delete(self, mem_id: str, reason: str) -> Dict[str, Any]:
        return self._service._propose_delete(self.actor, mem_id, reason)

    # SUMMARY

    def summary(self) -> Dict[str, Any]:
        return self._service._bridge.summary()

    def source_scores(self, domain: str, capability: str) -> Dict[str, int]:
        return self._service._bridge.source_scores(domain, capability)
