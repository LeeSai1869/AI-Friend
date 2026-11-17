import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

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


class CodingExplicitFileCreationTests(unittest.TestCase):
    class Broker:
        def __init__(self, files=None):
            self.files = dict(files or {})
            self.calls = []

        def with_workspace(self, _root):
            return self

        def call(self, operation, arguments):
            self.calls.append((operation, dict(arguments)))
            path = arguments["path"]
            if operation == "read_file":
                if path in self.files:
                    return {
                        "ok": True,
                        "data": {"path": path, "content": self.files[path]},
                    }
                return {"ok": False, "error": f"not found: {path}"}
            if operation == "write_file":
                self.files[path] = arguments["content"]
                return {"ok": True, "data": {"path": path}}
            raise AssertionError(f"unexpected broker operation: {operation}")

    def setUp(self):
        from coding.coding_engine import CodingOrgan

        self.organ = CodingOrgan()
        self.organ.project_context = SimpleNamespace(
            is_open=True,
            workspace=SimpleNamespace(root=Path("/tmp/coding-test-project")),
        )
        self.organ.project_broker = lambda broker: broker.with_workspace(
            Path("/tmp/coding-test-project")
        )

    def test_explicit_new_file_request_creates_empty_file_without_model(self):
        broker = self.Broker()
        result = self.organ.handle({
            "text": 'Please create a file named “lalalalalala.md"',
            "broker": broker,
            "caller": SimpleNamespace(),
        })

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["artifacts"], ["lalalalalala.md"])
        self.assertEqual(broker.files, {"lalalalalala.md": ""})
        self.assertEqual(
            [operation for operation, _ in broker.calls],
            ["read_file", "write_file"],
        )
        self.assertTrue(self.organ.verify(result)["ok"])

    def test_existing_file_is_not_overwritten(self):
        broker = self.Broker({"existing.txt": "preserve this"})
        result = self.organ.handle({
            "text": "Create a file named existing.txt",
            "broker": broker,
            "caller": SimpleNamespace(),
        })

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["operation"], "no_change")
        self.assertIn("No files were written", result["output"])
        self.assertEqual(broker.files["existing.txt"], "preserve this")
        self.assertEqual(
            [operation for operation, _ in broker.calls],
            ["read_file"],
        )

    def test_parser_rejects_traversal_and_content_requests(self):
        from coding.coding_engine import CodingOrgan

        self.assertEqual(
            CodingOrgan._explicit_empty_file_path(
                "Create a file named answer.txt with no content"
            ),
            "answer.txt",
        )
        self.assertIsNone(
            CodingOrgan._explicit_empty_file_path(
                "Create a file named ../outside.txt"
            )
        )
        self.assertIsNone(
            CodingOrgan._explicit_empty_file_path(
                "Create a file named answer.txt containing the answer"
            )
        )

    def test_creation_requires_an_open_coding_project(self):
        from coding.coding_engine import CodingOrgan

        organ = CodingOrgan()
        broker = self.Broker()
        result = organ.handle({
            "text": "Create a file named answer.txt",
            "broker": broker,
            "caller": SimpleNamespace(),
        })

        self.assertEqual(result["status"], "needs_answers")
        self.assertEqual(broker.calls, [])


if __name__ == "__main__":
    unittest.main()
