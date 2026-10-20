"""Central Mind Learner V1.

Learner selects worthwhile experience for governed permanent-memory proposal.

Important:
- Learner never creates Raw memory.
- Learner never writes Section 3 storage directly.
- Learner never self-authorizes persistence.
- Learner submits only through the approved MemoryClient interface.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


class Learner:

    def __init__(self, *, memory=None):
        self.memory = memory

    def learn(
        self,
        appraisal,
        *,
        response: Optional[Dict[str, Any]] = None,
        component: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if self.memory is None:
            return None

        if not getattr(appraisal, "reusable", False):
            return None

        response = response if isinstance(response, dict) else {}

        candidate = response.get("learning_candidate")
        if not isinstance(candidate, dict):
            # V1 refuses to invent permanent semantic knowledge merely from
            # an event. Appraisal may say an event is worth learning from,
            # but persistence requires an explicit compact knowledge candidate.
            return None

        title = str(candidate.get("title", "")).strip()
        content = str(candidate.get("content", "")).strip()

        if not title or not content:
            return None

        domain = candidate.get("domain") or getattr(appraisal, "domain", None) or "Mind"
        kind = candidate.get("kind", "pattern")
        tags = list(candidate.get("tags") or [])
        source_refs = list(candidate.get("source_refs") or [])

        for mem_id in getattr(appraisal, "memory_ids", []) or []:
            if mem_id not in source_refs:
                source_refs.append(mem_id)

        source = dict(candidate.get("source") or {})
        source.setdefault("type", "mind")
        source.setdefault("component", component or "central_mind")

        evidence = {
            "objective_outcome": getattr(appraisal, "objective_outcome", "unknown"),
            "verification_state": getattr(appraisal, "verification_state", "not_performed"),
            "disposition": getattr(appraisal, "disposition", "investigate"),
            "failure_code": getattr(appraisal, "failure_code", None),
            "reusable_reason": getattr(appraisal, "reusable_reason", ""),
        }

        # System learning is DERIVED. Raw belongs to Trainer Intake.
        return self.memory.propose_knowledge(
            title=title,
            content=content,
            domain=domain,
            kind=kind,
            requested_class="derived",
            originator=[{"type": "mind", "name": "central_mind"}],
            tags=tags,
            source_refs=source_refs,
            source=source,
            evidence=evidence,
            derivation_note=str(
                candidate.get(
                    "derivation_note",
                    "Derived from verified/appraised runtime experience.",
                )
            ),
        )
