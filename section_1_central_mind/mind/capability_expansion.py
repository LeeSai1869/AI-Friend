"""Central Mind Capability Expansion V1.

This component represents demonstrated capability gaps.

It does not:
- create code
- install capabilities
- grant permissions
- alter Inventory
- alter Guard policy
- authorize itself
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from typing import Any, Dict, List, Optional
import time


@dataclass
class CapabilityProposal:
    proposal_id: str
    objective: str
    requirement: str
    reason: str
    evidence: Dict[str, Any]
    existing_candidates: List[str]
    memory_refs: List[str]
    status: str
    created_at: float

    def as_dict(self):
        return asdict(self)


class CapabilityExpansion:

    def __init__(self, *, inventory=None):
        self.inventory = inventory
        self._proposals: List[CapabilityProposal] = []

    def propose_from_appraisal(self, appraisal) -> Optional[Dict[str, Any]]:
        gap = getattr(appraisal, "capability_gap", None)
        if not gap:
            return None

        existing = []
        if self.inventory is not None:
            try:
                existing = [
                    getattr(x, "name", str(x))
                    for x in self.inventory.all()
                ]
            except Exception:
                existing = []

        objective = str(getattr(appraisal, "objective", "") or "")
        material = f"{objective}|{gap}|{len(self._proposals)}".encode("utf-8")
        proposal_id = "cap_" + sha256(material).hexdigest()[:16]

        proposal = CapabilityProposal(
            proposal_id=proposal_id,
            objective=objective,
            requirement=str(gap),
            reason="demonstrated capability gap",
            evidence=dict(getattr(appraisal, "evidence", {}) or {}),
            existing_candidates=existing,
            memory_refs=list(getattr(appraisal, "memory_ids", []) or []),
            status="proposed",
            created_at=time.time(),
        )
        self._proposals.append(proposal)
        return proposal.as_dict()

    def proposals(self) -> List[Dict[str, Any]]:
        return [x.as_dict() for x in self._proposals]
