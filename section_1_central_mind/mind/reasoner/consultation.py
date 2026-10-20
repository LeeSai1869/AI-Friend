"""Generic domain consultation adapter for Central Mind Reasoner.

Consultation gathers bounded contextual evidence through ResourceSocket.
It is not execution of the human objective and does not itself verify,
appraise, learn from, or persist the consultation result.
"""
from __future__ import annotations

from typing import Any, Dict, Optional


class Consultation:
    def __init__(
        self,
        *,
        resource_socket=None,
        requirement_factory=None,
    ):
        self.resource_socket = resource_socket
        self.requirement_factory = requirement_factory

    def available(self) -> bool:
        return (
            self.resource_socket is not None
            and callable(
                getattr(
                    self.resource_socket,
                    "request",
                    None,
                )
            )
            and callable(self.requirement_factory)
        )

    def request(
        self,
        *,
        component: str,
        capability: str,
        subject: str,
        question: str,
        reasoning_state: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Request bounded evidence from one trusted domain."""

        if not self.available():
            return {
                "ok": False,
                "error": "consultation resource boundary unavailable",
            }

        component = str(component or "").strip()
        capability = str(capability or "").strip()
        subject = str(subject or "").strip()
        question = str(question or "").strip()

        if not component or not capability or not question:
            return {
                "ok": False,
                "error": "consultation request is incomplete",
            }

        try:
            requirement = self.requirement_factory(
                kind="domain",
                domain=component,
                capability=capability,
            )
        except Exception as exc:
            return {
                "ok": False,
                "error": (
                    "could not construct consultation requirement: "
                    + str(exc)
                ),
            }

        request = {
            "mode": "consultation",
            "consultation": {
                "capability": capability,
                "subject": subject,
                "question": question,
            },
            "context": dict(context or {}),
            "reasoning_state": dict(reasoning_state or {}),
        }

        # The existing domain connector requires a cognitive_plan argument.
        # Consultation deliberately supplies an empty mapping because this is
        # evidence gathering before a final CognitivePlan exists.
        try:
            response = self.resource_socket.request(
                requirement,
                request=request,
                cognitive_plan={},
            )
        except Exception as exc:
            return {
                "ok": False,
                "error": "domain consultation failed: " + str(exc),
            }

        if not isinstance(response, dict):
            return {
                "ok": False,
                "error": "domain consultation returned a non-mapping response",
            }

        if response.get("status") != "ok":
            return {
                "ok": False,
                "error": (
                    response.get("error")
                    or "domain consultation did not succeed"
                ),
                "response": response,
            }

        evidence = response.get("evidence")

        if evidence is None:
            return {
                "ok": False,
                "error": "domain consultation returned no evidence",
                "response": response,
            }

        return {
            "ok": True,
            "component": component,
            "capability": capability,
            "subject": subject,
            "evidence": evidence,
            "response": response,
        }
