"""Post-response correctness verification.

The Verifier delegates correctness checks to the organ that produced the
response. Authorization is not performed here: Guard authorization occurs
before protected actions execute through the ToolBroker.

Malformed verdicts and verifier exceptions fail closed.
"""
from __future__ import annotations

from typing import Any, Dict


class Verifier:

    @staticmethod
    def _valid_verdict(verdict: Any) -> bool:
        """Only an explicit boolean True is a passing verdict."""
        return (
            isinstance(verdict, dict)
            and verdict.get("ok") is True
        )

    def verify(
        self,
        response: Dict[str, Any],
        organ,
    ) -> Dict[str, Any]:
        result: Dict[str, Any] = {}

        try:
            organ_check = organ.verify(response)
        except Exception as exc:
            organ_check = {
                "ok": False,
                "reason": f"organ verify error: {exc}",
            }

        result["organ"] = organ_check
        result["ok"] = self._valid_verdict(organ_check)
        return result
