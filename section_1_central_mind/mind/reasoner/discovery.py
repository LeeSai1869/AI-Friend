"""Trusted discoverability analysis for Central Mind Reasoner.

Discovery decides whether proposed information gathering has a legitimate
trusted route.  It does not execute a consultation and does not decide the
final human clarification outcome.
"""
from __future__ import annotations

from typing import Any, Dict, List


class Discovery:
    def __init__(self, *, inventory=None):
        self.inventory = inventory

    def _component(self, name: str):
        if self.inventory is None:
            return None

        getter = getattr(self.inventory, "get", None)
        if not callable(getter):
            return None

        return getter(str(name or "").strip())

    def validate_consultation(
        self,
        proposal: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate one proposed domain consultation against Inventory."""

        if not isinstance(proposal, dict):
            return {
                "ok": False,
                "reason": "consultation proposal is not a mapping",
            }

        component = str(
            proposal.get("component") or ""
        ).strip()
        capability = str(
            proposal.get("capability") or ""
        ).strip()
        subject = str(
            proposal.get("subject") or ""
        ).strip()
        question = str(
            proposal.get("question") or ""
        ).strip()

        if not component:
            return {
                "ok": False,
                "reason": "consultation has no component",
            }

        if not capability:
            return {
                "ok": False,
                "reason": "consultation has no capability",
            }

        if not question:
            return {
                "ok": False,
                "reason": "consultation has no evidence question",
            }

        info = self._component(component)
        if info is None:
            return {
                "ok": False,
                "reason": f"unknown consultation component: {component!r}",
            }

        if getattr(info, "kind", None) != "domain":
            return {
                "ok": False,
                "reason": (
                    f"consultation component {component!r} "
                    "is not a domain"
                ),
            }

        manifest = getattr(info, "manifest", {}) or {}
        evidence_capabilities = manifest.get(
            "evidence_capabilities",
            {},
        )

        if not isinstance(evidence_capabilities, dict):
            evidence_capabilities = {}

        declaration = evidence_capabilities.get(capability)

        if declaration is None:
            return {
                "ok": False,
                "reason": (
                    f"domain {component!r} does not declare "
                    f"evidence capability {capability!r}"
                ),
            }

        if isinstance(declaration, str):
            description = declaration.strip()
            metadata = {}
        elif isinstance(declaration, dict):
            description = str(
                declaration.get("description") or ""
            ).strip()
            metadata = dict(declaration)
        else:
            return {
                "ok": False,
                "reason": (
                    f"domain {component!r} has malformed "
                    f"evidence capability {capability!r}"
                ),
            }

        return {
            "ok": True,
            "component": component,
            "capability": capability,
            "subject": subject,
            "question": question,
            "description": description,
            "evidence_metadata": metadata,
            "rationale": list(
                proposal.get("rationale", []) or []
            ),
        }

    def trusted_consultations(
        self,
        proposals: List[Dict[str, Any]],
        *,
        already_consulted: List[str] | None = None,
    ) -> Dict[str, Any]:
        """Partition proposals into trusted and rejected consultations."""

        trusted = []
        rejected = []
        seen = set()
        prior = set(
            str(item).strip()
            for item in (already_consulted or [])
            if str(item).strip()
        )

        for proposal in proposals or []:
            result = self.validate_consultation(proposal)

            if not result.get("ok"):
                rejected.append({
                    "proposal": (
                        dict(proposal)
                        if isinstance(proposal, dict)
                        else proposal
                    ),
                    "reason": result.get(
                        "reason",
                        "invalid consultation",
                    ),
                })
                continue

            identity = (
                result["component"],
                result["capability"],
                result["subject"],
                result["question"],
            )

            if identity in seen:
                continue

            # A component may be consulted again in a later cycle only when
            # the Reasoner has a materially different evidence question.
            # This function merely records prior consultation for the head;
            # it does not impose semantic policy itself.
            result["component_previously_consulted"] = (
                result["component"] in prior
            )

            seen.add(identity)
            trusted.append(result)

        return {
            "trusted": trusted,
            "rejected": rejected,
        }

    @staticmethod
    def unresolved_material_needs(
        information_needs: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Return material needs not explicitly covered by gathered evidence.

        This is deliberately conservative. Semantic equivalence is left to a
        later understanding cycle; Discovery only recognizes direct subject
        matches and never fabricates resolution.
        """

        covered = {
            str(item.get("subject") or "").strip()
            for item in (evidence or [])
            if isinstance(item, dict)
            and str(item.get("subject") or "").strip()
        }

        unresolved = []

        for item in information_needs or []:
            if not isinstance(item, dict):
                continue

            subject = str(
                item.get("subject") or ""
            ).strip()

            if not subject:
                continue

            if not bool(item.get("material", True)):
                continue

            if subject in covered:
                continue

            unresolved.append(dict(item))

        return unresolved
