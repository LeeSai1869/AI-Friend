"""Central Mind Self-Appraiser V1.

Appraisal is interpretation of an already observed result.

It is separate from:
- Guard authorization
- Verifier correctness checking
- Memory persistence
- Learner knowledge selection
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .cognition import Appraisal


class SelfAppraiser:

    def appraise(
        self,
        *,
        objective: str,
        response: Optional[Dict[str, Any]],
        verification: Optional[Dict[str, Any]],
        memory_ids=None,
        component: Optional[str] = None,
        domain: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> Appraisal:
        response = response if isinstance(response, dict) else {}
        verification = verification if isinstance(verification, dict) else {}
        memory_ids = list(memory_ids or [])

        verification_ok = verification.get("ok")

        if verification_ok is True:
            verification_state = "passed"
        elif verification_ok is False:
            verification_state = "failed"
        elif verification:
            verification_state = "insufficient"
        else:
            verification_state = "not_performed"

        status = str(response.get("status", "")).strip().lower()
        error = response.get("error")
        needs_answers = response.get("needs_answers")

        capability_gap = None
        failure_code = None

        if needs_answers:
            objective_outcome = "unknown"
            disposition = "clarify"
            failure_code = "insufficient_evidence"

        elif status in {"error", "failed", "failure"} or error:
            objective_outcome = "failure"
            disposition = "investigate"
            failure_code = self._classify_failure(response)

        elif verification_state == "failed":
            # Verification failure tells us the result cannot be accepted.
            # It does NOT mean verification itself failed to operate.
            objective_outcome = "unknown"
            disposition = "reject"
            failure_code = "verification_failed"

        elif status in {"partial"}:
            objective_outcome = "partial"
            disposition = "investigate"

        elif verification_state == "passed":
            objective_outcome = "success"
            disposition = "accept"

        else:
            objective_outcome = "unknown"
            disposition = "investigate"

        reusable, reusable_reason = self._reusable_value(
            objective=objective,
            response=response,
            verification_state=verification_state,
            objective_outcome=objective_outcome,
        )

        evidence = {
            "component": component,
            "response_status": response.get("status"),
            "verification": verification,
        }

        return Appraisal(
            objective=objective,
            objective_outcome=objective_outcome,
            verification_state=verification_state,
            disposition=disposition,
            failure_code=failure_code,
            reusable=reusable,
            reusable_reason=reusable_reason,
            capability_gap=capability_gap,
            provider=provider,
            domain=domain,
            memory_ids=memory_ids,
            evidence=evidence,
        )

    def capability_gap(
        self,
        *,
        objective: str,
        reason: str = "no capable component claimed request",
        memory_ids=None,
    ) -> Appraisal:
        return Appraisal(
            objective=objective,
            objective_outcome="unknown",
            verification_state="not_performed",
            disposition="investigate",
            failure_code="missing_capability",
            reusable=True,
            reusable_reason="demonstrated capability gap may prevent repeated failure",
            capability_gap=reason,
            memory_ids=list(memory_ids or []),
            evidence={"reason": reason},
        )

    @staticmethod
    def _classify_failure(response: Dict[str, Any]) -> str:
        text = " ".join(
            str(response.get(k, ""))
            for k in ("error", "reason", "message", "status")
        ).lower()

        mapping = (
            ("timeout", "timeout"),
            ("missing dependency", "missing_dependency"),
            ("modulenotfound", "missing_dependency"),
            ("import", "import_error"),
            ("syntax", "syntax_error"),
            ("permission", "authorization_denied"),
            ("denied", "authorization_denied"),
            ("resource", "resource_limit"),
            ("context", "context_mismatch"),
            ("logic", "logic_error"),
            ("wrong", "wrong_output"),
        )
        for needle, code in mapping:
            if needle in text:
                return code
        return "unknown"

    @staticmethod
    def _reusable_value(
        *,
        objective: str,
        response: Dict[str, Any],
        verification_state: str,
        objective_outcome: str,
    ):
        explicit = response.get("learning_candidate")
        if isinstance(explicit, dict):
            return True, "component supplied a structured learning candidate"

        if objective_outcome == "failure" and verification_state in {
            "passed",
            "failed",
        }:
            return True, "verified failure may prevent repeated unsuccessful work"

        return False, ""
