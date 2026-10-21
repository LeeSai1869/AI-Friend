"""Canonical Coding result-evidence verification; no authorization or execution."""
from typing import Any, Dict
from .tester import Tester


class Verifier:
    def verify(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Verify CodingOrgan success claims using explicit execution evidence."""
        if not isinstance(response, dict):
            return {"ok": False, "reason": "coding response is not a dictionary"}

        # Errors and clarification requests are not claims of successful coding.
        if response.get("status") != "ok":
            return {"ok": True, "reason": "response does not claim coding success"}

        operation = response.get("operation")
        artifacts = response.get("artifacts")

        if operation == "test_run":
            if artifacts == [] and Tester.passed(response.get("functional_tests") or {}):
                return {"ok": True, "reason": "functional tests executed and passed"}
            return {"ok": False, "reason": "test run lacks passing functional evidence"}

        if operation == "no_change":
            if artifacts == []:
                return {"ok": True, "reason": "no-change response confirms no files were written"}
            return {"ok": False, "reason": "no-change response must have an empty artifact list"}

        if operation != "code_change":
            return {"ok": False, "reason": "successful response lacks a recognized operation"}

        if (
            not isinstance(artifacts, list)
            or not artifacts
            or any(not isinstance(path, str) or not path.strip() for path in artifacts)
        ):
            return {"ok": False, "reason": "successful code change lacks valid artifact paths"}

        evidence = response.get("verification")
        if not isinstance(evidence, dict) or evidence.get("ok") is not True:
            return {"ok": False, "reason": "successful code change lacks passing verification evidence"}

        if not isinstance(evidence.get("reason"), str) or not evidence["reason"].strip():
            return {"ok": False, "reason": "verification evidence lacks a reason"}

        checks = evidence.get("checks")
        if not isinstance(checks, dict) or checks.get("file_writes") is not True:
            return {"ok": False, "reason": "file-write verification did not pass"}

        has_python = any(path.lower().endswith(".py") for path in artifacts)
        expected_syntax = "passed" if has_python else "not_applicable"

        if checks.get("python_syntax") != expected_syntax:
            return {
                "ok": False,
                "reason": f"Python syntax evidence must be {expected_syntax}",
            }

        functional = response.get("functional_tests")
        if functional is not None and not Tester.passed(functional):
            return {"ok": False, "reason": "functional test evidence did not pass"}
        return {"ok": True, "reason": "coding evidence passed validation"}
