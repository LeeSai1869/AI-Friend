"""The Organ interface.

Every organ — domains, tools, models, sources, guards, chatbox,
trainer — implements this interface. The mind calls only through
these six methods. Nothing else.

The mind is reader of all and writer of nothing.
The mind is creator of all but killer of nothing.
The mind upgrades information, not downgrade.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


class Organ:
    """Base class for every organ in Central Mind.

    Subclasses override every method. The default implementations
    are conservative: they refuse to act unless the subclass
    explicitly enables the capability.
    """

    # ---- identity -------------------------------------------------

    name: str = "unnamed"
    kind: str = "organ"           # "domain" | "tool" | "model" | "source" | "guard" | "chatbox" | "trainer"
    scope: str = "outside_guards" # "outside_guards" | "inside_guards"

    capabilities: List[str] = []
    keywords: List[str] = []

    # ---- orchestration (5 methods) --------------------------------

    def can_handle(self, request: Dict[str, Any]) -> bool:
        """Does this organ claim to handle this request?"""
        return False

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the request. Return a response dict.

        Response shape (any organ may return any of these keys):
          {
            "status": "ok" | "needs_answers" | "error" | "no_handler",
            "output": <any>,
            "questions": [ {attribute, options, default}, ... ],
            "error": "message",
            "artifacts": [ ... ]
          }
        """
        return {"status": "no_handler"}

    def questions(self, request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """What does this organ need from the user to proceed?"""
        return []

    def verify(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Is this response valid? Return {ok: bool, reason: str}."""
        return {"ok": True, "reason": ""}

    def evaluate_knowledge(
        self,
        proposal: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Evaluate imported knowledge when this organ can test it.

        The default is deliberately non-passing.  A component must return
        explicit evidence before Central Mind may promote knowledge beyond
        raw/unverified memory.
        """
        return {
            "ok": False,
            "testable": False,
            "reason": "organ provides no knowledge evaluator",
            "evidence": {},
        }

    # ---- evolution (1 method) -------------------------------------

    def receive_proposal(
        self,
        proposal: Dict[str, Any],
        approval: str,
        authority: str,
    ) -> Dict[str, Any]:
        """Receive a change proposal from the mind or trainer.

        proposal:  see mind/proposer.py for the shape.
        approval:  "auto" (mind-applied) | "trainer" (trainer-approved)
        authority: "mind" | "trainer"

        The organ decides whether to accept based on its own policy:
          - inside_guards organs accept only authority="trainer"
          - outside_guards organs accept "mind" for upgrades, "trainer" for anything
          - deletion is never accepted by any organ

        Returns {status: "ok" | "refused" | "error", reason: str}
        """
        return {"status": "refused", "reason": "organ does not accept proposals"}