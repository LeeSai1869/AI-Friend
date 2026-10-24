"""Gated proposal queue for Central Mind."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


KIND_SELF_DIRECTED = "self_directed"
KIND_REMOVAL = "removal"
KIND_FEATURE_EXPANSION = "feature_expansion"
VALID_KINDS = frozenset({
    KIND_SELF_DIRECTED,
    KIND_REMOVAL,
    KIND_FEATURE_EXPANSION,
})

VALID_STATUSES = frozenset({
    "proposed", "under_audit", "audit_passed", "audit_failed",
    "audit_needs_evidence", "approved", "rejected", "deferred", "expired",
})

VALID_DECISIONS = frozenset({"approve", "reject", "defer"})


class ProposalContractError(ValueError):
    pass


@dataclass
class Proposal:
    proposal_id: str
    kind: str
    producer: str
    objective: str
    proposed_action: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    scope: Dict[str, Any] = field(default_factory=dict)
    risk: Dict[str, Any] = field(default_factory=dict)
    dependents: List[str] = field(default_factory=list)
    affects_central_mind: bool = False
    status: str = "proposed"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    audit_verdict: Optional[Dict[str, Any]] = None
    administrator_decision: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.proposal_id or not isinstance(self.proposal_id, str):
            raise ProposalContractError("proposal_id required")
        if self.kind not in VALID_KINDS:
            raise ProposalContractError(f"unknown kind: {self.kind!r}")
        if self.status not in VALID_STATUSES:
            raise ProposalContractError(f"unknown status: {self.status!r}")
        if not self.producer: raise ProposalContractError("producer required")
        if not self.objective: raise ProposalContractError("objective required")
        if not self.proposed_action: raise ProposalContractError("proposed_action required")

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProposalQueue:
    MAX_PROPOSALS = 1000

    def __init__(self, max_proposals: int = MAX_PROPOSALS):
        self._max = max(1, int(max_proposals))
        self._items: Dict[str, Proposal] = {}
        self._order: List[str] = []

    def append(self, *, kind, producer, objective, proposed_action,
               evidence=None, scope=None, risk=None, dependents=None,
               affects_central_mind=False) -> str:
        pid = "prop_" + uuid.uuid4().hex
        p = Proposal(
            proposal_id=pid, kind=kind, producer=producer,
            objective=objective, proposed_action=proposed_action,
            evidence=dict(evidence or {}), scope=dict(scope or {}),
            risk=dict(risk or {}), dependents=list(dependents or []),
            affects_central_mind=bool(affects_central_mind),
        )
        self._items[pid] = p
        self._order.append(pid)
        while len(self._order) > self._max:
            self._items.pop(self._order.pop(0), None)
        return pid

    def get(self, pid: str) -> Optional[Proposal]:
        return self._items.get(str(pid or ""))

    def list(self, *, status: Optional[str] = None) -> List[Dict[str, Any]]:
        out = []
        for pid in self._order:
            p = self._items.get(pid)
            if p is None: continue
            if status is not None and p.status != status: continue
            out.append(p.as_dict())
        return out

    def record_audit(self, pid: str, *, verdict: Dict[str, Any]) -> Dict[str, Any]:
        p = self._require(pid)
        if p.status not in {"proposed", "audit_needs_evidence", "audit_failed"}:
            raise ProposalContractError(
                f"status {p.status!r} cannot be audited"
            )
        p.audit_verdict = dict(verdict)
        v = str(verdict.get("verdict") or "").strip()
        p.status = ("audit_passed" if v == "pass"
                    else "audit_needs_evidence" if v == "needs_more_evidence"
                    else "audit_failed")
        p.updated_at = time.time()
        return p.as_dict()

    def record_decision(self, pid: str, *, decision, actor, reason) -> Dict[str, Any]:
        p = self._require(pid)
        if decision not in VALID_DECISIONS:
            raise ProposalContractError(f"unknown decision: {decision!r}")
        if not reason or not reason.strip():
            raise ProposalContractError("reason required")
        if not actor or not actor.strip():
            raise ProposalContractError("actor required")
        if p.status != "audit_passed":
            raise ProposalContractError(f"status {p.status!r} rejects decision")
        p.administrator_decision = {
            "decision": decision, "actor": actor, "reason": reason,
            "decided_at": time.time(),
        }
        p.status = {"approve": "approved", "reject": "rejected", "defer": "deferred"}[decision]
        p.updated_at = time.time()
        return p.as_dict()

    def _require(self, pid: str) -> Proposal:
        p = self.get(pid)
        if p is None:
            raise ProposalContractError(f"unknown proposal_id: {pid!r}")
        return p
