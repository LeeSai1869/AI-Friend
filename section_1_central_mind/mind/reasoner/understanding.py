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
            "When the user asks whether AI Friend can access, inspect, or act "
            "on something, do not answer from assumption or return a "
            "communication-only plan if the trusted capability catalog "
            "describes a relevant capability or live-state evidence source. "
            "Use the capability descriptions to distinguish similarly named "
            "operations and identify which domain owns the requested data. "
            "Propose a matching read-only evidence consultation when one is "
            "declared; UI observations alone do not prove that a resource is "
            "available. If the catalog declares a relevant execution "
            "capability but no evidence capability, plan a safe capability "
            "check or ask a focused clarification instead of claiming the "
            "capability is unavailable. "
            "Never invent identifiers. A candidate step kind is domain or "
            "communicate. A communicate step has null component and capability. "
            "The active UI window and its project details are observations, "
            "not domain-routing instructions. Choose domains from the trusted "
            "capability catalog according to the user's objective; the UI does "
            "not choose a domain. Catalog entries with purpose='evidence' may "
            "only be used for consultations, while purpose='execution' entries "
            "may be used for candidate steps. Consult a domain for discoverable "
            "context, such as whether its project is open, before asking the "
            "human for information the domain can provide. If evidence shows "
            "that a needed project is not open, ask the human to open/select it. "
            "Other domain steps may be included when the task genuinely "
            "requires multiple domains. "
            "Do not ask the human for a detail that has a conventional default that a competent practitioner would simply choose, such as which standard tool or framework to use, where a new file belongs, or naming, formatting and style. "
            "Prefer the convention that the project, the capability descriptions or the supplied evidence already point to, and otherwise the most widely used one. "
            "Mark such a need with material false, state each assumption inside the objective of the step that depends on it so the executing domain receives it, and mention it in rationale. "
            "Ask the human only when the answer would change what the user wants, when a wrong guess could lose or overwrite existing work, or when nothing in the request, context or evidence indicates a sensible choice. "
            "If prior_understanding contains validation_feedback, Central Mind rejected those candidate steps for the reasons listed. "
            "Propose corrected steps that use only components of kind domain from the trusted capability catalog, or a communicate step when no domain applies. "
            "Return JSON only with keys: objective_summary, requirements, "
            "constraints, ambiguities, acceptance_checks, information_needs, consultations, "
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

        system += (
            " Preserve every explicit user requirement, exact signature and constraint. "
            "acceptance_checks is optional: a list of objects with id, requirement_ids "
            "(requirements are numbered R1, R2 in order), kind and payload. Use only "
            "checks supported by the selected domain's declared acceptance_check_contracts. "
            "Use that domain's payload specification; Mind assigns no domain-specific "
            "meaning to payload fields. A check may name its executing step_id. "
            "Extract expected behavior from explicit requirements; never invent ambiguous expected results."
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

        expected_keys = (
            "objective_summary",
            "requirements",
            "information_needs",
            "consultations",
            "candidate_steps",
            "clarification_candidates",
        )
        if not any(key in proposed for key in expected_keys):
            # The resource repeated its input or returned an unrelated object.
            # Ask once more before treating the understanding as unusable.
            try:
                raw = self.semantic_resource(
                    system=system,
                    messages=[
                        {
                            "role": "user",
                            "content": json.dumps(
                                payload,
                                ensure_ascii=False,
                                default=str,
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                "Your previous reply did not contain the requested "
                                "analysis. Reply with ONE JSON object with exactly "
                                "the requested keys, starting with objective_summary. "
                                "Do not repeat the input."
                            ),
                        },
                    ],
                )
                proposed = json.loads(self._strip_json_fence(raw))
            except Exception as exc:
                return {
                    "error": (
                        "semantic understanding retry failed: "
                        + str(exc)
                    ),
                }
            if not isinstance(proposed, dict) or not any(
                key in proposed for key in expected_keys
            ):
                return {
                    "error": (
                        "semantic understanding did not contain the requested analysis"
                    ),
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
            "acceptance_checks": proposed.get("acceptance_checks", []),
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
