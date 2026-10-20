import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "section_1_central_mind"))
sys.path.insert(0, str(ROOT / "section_5_domains"))

from coding.coding_engine import _assess_coding_result


class CodingResultAssessmentTests(unittest.TestCase):
    def test_successful_python_write_and_syntax_check(self):
        result = _assess_coding_result(
            [{"path": "example.py", "ok": True}],
            {"ok": True, "data": {"returncode": 0}},
            syntax_check_required=True,
        )
        self.assertTrue(result["ok"])
        self.assertIn("syntax check succeeded", result["reason"])

    def test_failed_write_is_rejected(self):
        result = _assess_coding_result(
            [{"path": "example.py", "ok": False}],
            {"ok": True, "data": {"returncode": 0}},
            syntax_check_required=True,
        )
        self.assertFalse(result["ok"])
        self.assertIn("write failed", result["reason"])

    def test_failed_syntax_check_is_rejected(self):
        result = _assess_coding_result(
            [{"path": "example.py", "ok": True}],
            {"ok": False, "data": {"returncode": 1}},
            syntax_check_required=True,
        )
        self.assertFalse(result["ok"])
        self.assertIn("syntax check failed", result["reason"])

    def test_missing_required_syntax_result_is_rejected(self):
        result = _assess_coding_result(
            [{"path": "example.py", "ok": True}],
            None,
            syntax_check_required=True,
        )
        self.assertFalse(result["ok"])
        self.assertIn("no valid result", result["reason"])

    def test_malformed_syntax_result_is_rejected(self):
        result = _assess_coding_result(
            [{"path": "example.py", "ok": True}],
            {"ok": True},
            syntax_check_required=True,
        )
        self.assertFalse(result["ok"])
        self.assertIn("successful exit code", result["reason"])

    def test_non_python_write_does_not_claim_syntax_was_checked(self):
        result = _assess_coding_result(
            [{"path": "notes.txt", "ok": True}], None
        )
        self.assertTrue(result["ok"])
        self.assertIn("no Python syntax check", result["reason"])

    def test_empty_write_list_is_rejected(self):
        result = _assess_coding_result([], None)
        self.assertFalse(result["ok"])

    def test_malformed_write_result_is_rejected(self):
        result = _assess_coding_result([None], None)
        self.assertFalse(result["ok"])
        self.assertIn("malformed", result["reason"])


class CodingOrganVerificationTests(unittest.TestCase):
    def setUp(self):
        from coding.coding_engine import CodingOrgan
        self.organ = CodingOrgan()

    def test_success_without_evidence_is_rejected(self):
        result = self.organ.verify({
            "status": "ok",
            "operation": "code_change",
            "artifacts": ["example.py"],
        })
        self.assertFalse(result["ok"])

    def test_valid_python_change_evidence_is_accepted(self):
        result = self.organ.verify({
            "status": "ok",
            "operation": "code_change",
            "artifacts": ["example.py"],
            "verification": {
                "ok": True,
                "reason": "File write and syntax check succeeded",
                "checks": {
                    "file_writes": True,
                    "python_syntax": "passed",
                },
            },
        })
        self.assertTrue(result["ok"])

    def test_python_change_without_passed_syntax_is_rejected(self):
        result = self.organ.verify({
            "status": "ok",
            "operation": "code_change",
            "artifacts": ["example.py"],
            "verification": {
                "ok": True,
                "reason": "Only the write was checked",
                "checks": {
                    "file_writes": True,
                    "python_syntax": "not_applicable",
                },
            },
        })
        self.assertFalse(result["ok"])

    def test_non_python_change_does_not_claim_python_syntax_check(self):
        result = self.organ.verify({
            "status": "ok",
            "operation": "code_change",
            "artifacts": ["notes.txt"],
            "verification": {
                "ok": True,
                "reason": "File write succeeded",
                "checks": {
                    "file_writes": True,
                    "python_syntax": "not_applicable",
                },
            },
        })
        self.assertTrue(result["ok"])

    def test_no_change_response_is_accepted(self):
        result = self.organ.verify({
            "status": "ok",
            "operation": "no_change",
            "artifacts": [],
        })
        self.assertTrue(result["ok"])


if __name__ == "__main__":
    unittest.main()
