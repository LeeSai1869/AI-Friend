import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CENTRAL_MIND = PROJECT_ROOT / "section_1_central_mind"
sys.path.insert(0, str(CENTRAL_MIND))

from mind.verifier import Verifier


class StubOrgan:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    def verify(self, response):
        if self.error:
            raise RuntimeError(self.error)
        return self.result



class VerifierTests(unittest.TestCase):
    def test_explicit_pass_is_accepted(self):
        result = Verifier().verify(
            {"status": "ok", "output": "answer"},
            StubOrgan({"ok": True, "reason": "check passed"}),
        )
        self.assertTrue(result["ok"])

    def test_explicit_failure_is_rejected(self):
        result = Verifier().verify(
            {"status": "ok"}, StubOrgan({"ok": False, "reason": "failed"})
        )
        self.assertFalse(result["ok"])

    def test_missing_ok_field_is_not_a_pass(self):
        result = Verifier().verify(
            {"status": "ok"}, StubOrgan({"reason": "no verdict"})
        )
        self.assertFalse(result["ok"])

    def test_non_dictionary_verdict_is_not_a_pass(self):
        result = Verifier().verify({"status": "ok"}, StubOrgan("passed"))
        self.assertFalse(result["ok"])

    def test_exception_is_rejected(self):
        result = Verifier().verify(
            {"status": "ok"}, StubOrgan(error="verification crashed")
        )
        self.assertFalse(result["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
