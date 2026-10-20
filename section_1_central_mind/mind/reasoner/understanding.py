"""Semantic understanding for Central Mind Reasoner.

A subordinate reasoning resource may propose interpretations, information
needs, consultations and candidate steps.  It has no authority to decide
clarification, execution, capability validity, or the final CognitivePlan.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional


class SemanticUnderstanding:
    def __init__(
        self,
        *,
        inventory=None,
        semantic_resource: Optional[Callable[..., str]] = None,
    ):
        self.inventory = inventory
        self.semantic_resource = semantic_resource

    @staticmethod
    def _string_list(value: Any) -> List[str]:
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            return []
        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    @staticmethod
    def _confidence(value: Any) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = 0.0
        return max(0.0, min(1.0, number))

    @staticmethod
    def _strip_json_fence(raw: Any) -> str:
        text = str(raw or "").strip()
        if not text.startswith("```"):
            return text

        lines = text.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()

    def _catalog(self) -> List[Dict[str, Any]]:
        if self.inventory is None:
            return []

        catalog_fn = getattr(
            self.inventory,
            "capability_catalog",
            None,
        )
        if not callable(catalog_fn):
            return []

        rows = catalog_fn()
        return [
            dict(row)
            for row in rows
            if isinstance(row, dict)
        ]

    def propose(
        self,
        *,
        objective: str,
        supplied_context: Dict[str, Any],
        recalled_memory: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        prior_understanding: Optional[Dict[str, Any]] = None,
        capability_catalog: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Request one semantic proposal from a subordinate resource."""

        text = str(objective or "").strip()
        if not text:
            return {
                "objective_summary": "",
                "requirements": [],
                "constraints": [],
                "ambiguities": [],
                "information_needs": [{
                    "subject": "objective",
                    "reason": "no objective was supplied",
                    "material": True,
                }],
                "consultations": [],
                "candidate_steps": [],
                "clarification_candidates": [{
                    "attribute": "objective",
                    "question": "What would you like me to do?",
                    "options": [],
                    "default": None,
                }],
                "understanding_confidence": 0.0,
                "rationale": ["the objective is empty"],
            }

        catalog = (
            [
                dict(row)
                for row in capability_catalog
                if isinstance(row, dict)
            ]
            if isinstance(capability_catalog, list)
            else self._catalog()
        )

        if not catalog:
            return {
                "error": "trusted capability catalog unavailable or empty",
            }

        if not callable(self.semantic_resource):
            return {
                "error": "semantic understanding resource unavailable",
            }

        system = (
            "You are a subordinate semantic reasoning resource for AI Friend "
            "Central Mind. You have no authority and execute nothing. Central "
            "Mind owns understanding, investigation, clarification decisions, "
            "planning and execution. Your job is to PROPOSE a semantic "
            "interpretation of the current reasoning state. Use supplied "
            "context, recalled memory and gathered evidence as evidence, but "
            "do not invent facts. Distinguish an information need from a human "
            "clarification requirement: you may identify information that is "
            "not yet known, but you must not decide that the human must answer "
            "it. If an information need may be discoverable from a trusted "
            "domain or capability, propose a consultation first. A consultation "
            "is for context or evidence gathering, not completion of the user's "
            "requested action. Candidate execution steps must use component and "
            "capability identifiers only from the trusted capability catalog. "
            "Never invent identifiers. A candidate step kind is domain or "
            "communicate. A communicate step has null component and capability. "
            "Return JSON only with keys: objective_summary, requirements, "
            "constraints, ambiguities, information_needs, consultations, "
            "candidate_steps, clarification_candidates, "
            "understanding_confidence, rationale. information_needs must be a "
            "list of objects with keys subject, reason, material. consultations "
            "must be a list of objects with keys component, capability, subject, "
            "question, rationale. candidate_steps must be a list of objects "
            "with keys step_id, objective, kind, component, capability, "
            "depends_on, requirements, constraints, expected_outcome, "
            "confidence, rationale. clarification_candidates must be a list of "
            "objects with keys attribute, question, options, default."
        )

        payload = {
            "objective": text,
            "supplied_context": dict(supplied_context or {}),
            "recalled_memory": list(recalled_memory or []),
            "evidence": list(evidence or []),
            "prior_understanding": dict(prior_understanding or {}),
            "trusted_capability_catalog": catalog,
        }

        try:
            raw = self.semantic_resource(
                system=system,
                messages=[{
                    "role": "user",
                    "content": json.dumps(
                        payload,
                        ensure_ascii=False,
                        default=str,
                    ),
                }],
            )
        except Exception as exc:
            return {
                "error": (
                    "semantic understanding unavailable: "
                    + str(exc)
                ),
            }

        text_result = self._strip_json_fence(raw)

        try:
            proposed = json.loads(text_result)
        except Exception as exc:
            return {
                "error": (
                    "semantic understanding returned invalid structured JSON: "
                    + str(exc)
                ),
            }

        if not isinstance(proposed, dict):
            return {
                "error": "semantic understanding returned non-object JSON",
            }

        information_needs = []
        raw_needs = proposed.get("information_needs", [])
        if isinstance(raw_needs, list):
            for item in raw_needs:
                if not isinstance(item, dict):
                    continue
                subject = str(item.get("subject") or "").strip()
                reason = str(item.get("reason") or "").strip()
                if not subject:
                    continue
                information_needs.append({
                    "subject": subject,
                    "reason": reason,
                    "material": bool(item.get("material", True)),
                })

        consultations = []
        raw_consultations = proposed.get("consultations", [])
        if isinstance(raw_consultations, list):
            for item in raw_consultations:
                if not isinstance(item, dict):
                    continue

                component = str(
                    item.get("component") or ""
                ).strip()
                capability = str(
                    item.get("capability") or ""
                ).strip()
                subject = str(
                    item.get("subject") or ""
                ).strip()
                question = str(
                    item.get("question") or ""
                ).strip()

                if not component or not capability or not question:
                    continue

                consultations.append({
                    "component": component,
                    "capability": capability,
                    "subject": subject,
                    "question": question,
                    "rationale": self._string_list(
                        item.get("rationale")
                    ),
                })

        clarification_candidates = []
        raw_questions = proposed.get(
            "clarification_candidates",
            [],
        )
        if isinstance(raw_questions, list):
            for index, item in enumerate(raw_questions):
                if not isinstance(item, dict):
                    continue

                question = str(
                    item.get("question") or ""
                ).strip()
                if not question:
                    continue

                options = item.get("options", [])
                if not isinstance(options, list):
                    options = []

                clarification_candidates.append({
                    "attribute": str(
                        item.get("attribute")
                        or f"clarification_{index + 1}"
                    ).strip(),
                    "question": question,
                    "options": [
                        str(option)
                        for option in options
                        if str(option).strip()
                    ],
                    "default": item.get("default"),
                })

        candidate_steps = []
        raw_steps = proposed.get("candidate_steps", [])
        if isinstance(raw_steps, list):
            for index, item in enumerate(raw_steps):
                if not isinstance(item, dict):
                    continue

                candidate_steps.append({
                    "step_id": str(
                        item.get("step_id")
                        or f"step_{index + 1}"
                    ).strip(),
                    "objective": str(
                        item.get("objective")
                        or objective
                    ).strip(),
                    "kind": str(
                        item.get("kind")
                        or "domain"
                    ).strip().lower(),
                    "component": item.get("component"),
                    "capability": item.get("capability"),
                    "depends_on": self._string_list(
                        item.get("depends_on")
                    ),
                    "requirements": self._string_list(
                        item.get("requirements")
                    ),
                    "constraints": self._string_list(
                        item.get("constraints")
                    ),
                    "expected_outcome": str(
                        item.get("expected_outcome")
                        or ""
                    ).strip(),
                    "confidence": self._confidence(
                        item.get("confidence")
                    ),
                    "rationale": self._string_list(
                        item.get("rationale")
                    ),
                })

        return {
            "objective_summary": str(
                proposed.get("objective_summary")
                or objective
            ).strip(),
            "requirements": self._string_list(
                proposed.get("requirements")
            ),
            "constraints": self._string_list(
                proposed.get("constraints")
            ),
            "ambiguities": self._string_list(
                proposed.get("ambiguities")
            ),
            "information_needs": information_needs,
            "consultations": consultations,
            "candidate_steps": candidate_steps,
            "clarification_candidates": clarification_candidates,
            "understanding_confidence": self._confidence(
                proposed.get("understanding_confidence")
            ),
            "rationale": self._string_list(
                proposed.get("rationale")
            ),
        }
