"""Independent Self-Assessment loop for Central Mind."""
from __future__ import annotations

from typing import Any, Dict


class SelfAssessmentLoop:
    """Review operational evidence and submit audited admin proposals."""

    def __init__(self, *, scorer, proposal_queue, audit_stage, inventory):
        self.scorer = scorer
        self.proposal_queue = proposal_queue
        self.audit_stage = audit_stage
        self.inventory = inventory

    def run(self) -> Dict[str, Any]:
        recent = getattr(self.scorer, "recent", None)
        if not callable(recent):
            return {
                "status": "assessment_unavailable",
                "proposals": [],
                "reason": "scorer does not expose recent experience",
            }
        events = recent(limit=64)
        failures = {}
        for event in events:
            if not isinstance(event, dict):
                continue
            if event.get("event") != "cognitive_result":
                continue
            outcome = event.get("objective_outcome")
            verification = event.get("verification_state")
            if outcome not in {"failure", "partial"} and verification != "failed":
                continue
            component = str(event.get("originating_component") or "unknown")
            failure_code = str(event.get("failure_code") or "unclassified")
            key = (component, failure_code)
            failures[key] = failures.get(key, 0) + 1

        repeated = [
            (component, code, count)
            for (component, code), count in failures.items()
            if count >= 3
        ]
        if not repeated:
            return {
                "status": "assessed",
                "proposals": [],
                "reason": "no repeated verified failure pattern",
            }

        submitted = []
        for component, failure_code, count in repeated:
            signal = f"{component}:{failure_code}"
            existing = next(
                (
                    row for row in self.proposal_queue.list()
                    if row.get("kind") == "self_directed"
                    and row.get("scope", {}).get("signal") == signal
                    and row.get("status") not in {
                        "rejected", "deferred", "expired",
                    }
                ),
                None,
            )
            if existing is not None:
                submitted.append(existing)
                continue

            dependents = [
                getattr(item, "name", "")
                for item in self.inventory.all()
                if getattr(item, "name", "")
            ]
            proposal_id = self.proposal_queue.append(
                kind="self_directed",
                producer="central_mind.self_assessment",
                objective=f"Review repeated {failure_code} in {component}",
                proposed_action=(
                    "Administrator review required: investigate the repeated "
                    "failure and propose a bounded improvement. This assessment "
                    "does not modify Central Mind."
                ),
                evidence={
                    "reason": "Repeated operational failures need review.",
                    "observed_signal": {
                        "component": component,
                        "failure_code": failure_code,
                        "occurrences": count,
                    },
                    "dependents_scan": dependents,
                    "affects_central_mind_acknowledged": True,
                },
                scope={
                    "signal": signal,
                    "target": "central_mind_review",
                    "requires_administrator_permission": True,
                },
                risk={"level": "low"},
                dependents=dependents,
                affects_central_mind=True,
            )
            proposal = self.proposal_queue.get(proposal_id)
            verdict = self.audit_stage.evaluate(proposal)
            submitted.append(
                self.proposal_queue.record_audit(
                    proposal_id,
                    verdict=verdict,
                )
            )

        return {
            "status": "assessed",
            "proposals": submitted,
        }
