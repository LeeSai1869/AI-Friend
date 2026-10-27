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


class FeatureExpansionLoop:

    def __init__(self, *, inventory=None, proposal_queue=None, audit_stage=None):
        self.inventory = inventory
        self.proposal_queue = proposal_queue
        self.audit_stage = audit_stage
        self._proposals: List[CapabilityProposal] = []

    def propose_from_appraisal(self, appraisal) -> Optional[Dict[str, Any]]:
        gap = getattr(appraisal, "capability_gap", None)
        if not gap:
            return None

        existing = []
        if self.inventory is not None:
            existing = [
                getattr(x, "name", str(x))
                for x in self.inventory.all()
            ]

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
        result = proposal.as_dict()
        if self.proposal_queue is not None:
            from ..proposals import KIND_FEATURE_EXPANSION

            dependents = list(existing)
            proposal_id = self.proposal_queue.append(
                kind=KIND_FEATURE_EXPANSION,
                producer="central_mind.feature_expansion",
                objective=f"Expand capability: {objective[:160]}",
                proposed_action=(
                    "Build and validate a new compatible plug for the "
                    "demonstrated capability gap."
                ),
                evidence={
                    "reason": "A runtime capability gap was observed.",
                    "observed_signal": {
                        "requirement": str(gap),
                        "failure_code": getattr(appraisal, "failure_code", None),
                    },
                    "dependents_scan": dependents,
                },
                scope={
                    "operation": "install",
                    "target": "unselected",
                    "prohibited": [
                        "delete",
                        "section_1_central_mind",
                        "section_3_memory",
                        "documents",
                    ],
                },
                risk={"level": "low"},
                dependents=dependents,
            )
            result["proposal_id"] = proposal_id
            if self.audit_stage is not None:
                queued = self.proposal_queue.get(proposal_id)
                verdict = self.audit_stage.evaluate(queued)
                result["audit"] = self.proposal_queue.record_audit(
                    proposal_id,
                    verdict=verdict,
                )["audit_verdict"]
        return result

    def proposals(self) -> List[Dict[str, Any]]:
        return [x.as_dict() for x in self._proposals]


CapabilityExpansion = FeatureExpansionLoop
