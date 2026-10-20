from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from section_1_central_mind.guard.contract import GuardPrincipal
from section_1_central_mind.guard.layer import GuardLayer
from section_1_central_mind.guard.production_policy import (
    build_production_effect_policy,
    build_production_guard_policy,
)
from section_1_central_mind.mind.broker import ToolBroker
from section_1_central_mind.mind.inventory import Inventory


class CodingV1ConstrainedExecutionTests(unittest.TestCase):

    def setUp(self):
        self.project_root = Path(__file__).resolve().parents[1]
        self.tools_dir = self.project_root / "section_8_tools"

        # ToolBroker.workspace_root is the project security root, not an
        # arbitrary scratch directory. Keep test material inside that root.
        self.test_parent = (
            self.project_root
            / ".central_mind"
            / "test_runtime"
        )
        self.test_parent.mkdir(parents=True, exist_ok=True)

        self.test_root = Path(
            tempfile.mkdtemp(
                prefix="coding_v1_",
                dir=self.test_parent,
            )
        )

    def tearDown(self):
        shutil.rmtree(self.test_root, ignore_errors=True)

    def _principal(self, role):
        return GuardPrincipal(
            principal_id=f"{role}.coding-v1-test",
            kind="human",
            role=role,
            authenticated=True,
            source="auth_service",
        )

    def _broker(self, role="trainer"):
        inventory = Inventory(self.project_root).discover()

        guard = GuardLayer(
            self.project_root,
            policy=build_production_guard_policy(),
            effect_policy=build_production_effect_policy(),
        )

        return ToolBroker(
            workspace_root=self.project_root,
            tools_dir=self.tools_dir,
            guard=guard,
            principal=self._principal(role),
            inventory=inventory,
        )

    def _relative(self, path):
        return str(
            Path(path).resolve().relative_to(self.project_root)
        )

    def test_trainer_has_narrow_test_authority_but_not_general_execute(self):
        policy = build_production_guard_policy()
        trainer = self._principal("trainer")

        narrow = policy.evaluate(
            trainer,
            ("code.test.execute",),
        )
        broad = policy.evaluate(
            trainer,
            ("process.execute",),
        )

        self.assertTrue(narrow.allowed)
        self.assertFalse(broad.allowed)

    def test_general_run_command_remains_denied(self):
        broker = self._broker()

        result = broker.bind_central_mind().call(
            "run_command",
            {
                "command": [
                    "python3",
                    "-c",
                    "print('should not run')",
                ]
            },
        )

        self.assertFalse(result["ok"])
        self.assertIn("guard denied", result["error"])
        self.assertIn("process.execute", result["error"])

    def test_python_compile_profile_succeeds_for_workspace_python(self):
        target = self.test_root / "good.py"
        target.write_text("value = 1\n")

        broker = self._broker()
        result = broker.bind_central_mind().call(
            "run_python_compile",
            {"paths": [self._relative(target)]},
        )

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["data"]["returncode"], 0)
        self.assertEqual(
            result["data"]["command"][:3],
            ["python3", "-m", "py_compile"],
        )

    def test_python_compile_profile_reports_invalid_python(self):
        target = self.test_root / "bad.py"
        target.write_text(
            "def broken(:\n"
            "    pass\n"
        )

        broker = self._broker()
        result = broker.bind_central_mind().call(
            "run_python_compile",
            {"paths": [self._relative(target)]},
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["data"]["returncode"], 1)

    def test_python_compile_rejects_non_python_target_before_execution(self):
        target = self.test_root / "note.txt"
        target.write_text("hello\n")

        broker = self._broker()
        result = broker.bind_central_mind().call(
            "run_python_compile",
            {"paths": [self._relative(target)]},
        )

        self.assertFalse(result["ok"])
        self.assertIn(
            "effect preflight failed",
            result["error"],
        )
        self.assertIn(
            "only .py files",
            result["error"],
        )

    def test_python_compile_rejects_workspace_escape(self):
        broker = self._broker()

        result = broker.bind_central_mind().call(
            "run_python_compile",
            {"paths": ["../outside.py"]},
        )

        self.assertFalse(result["ok"])
        self.assertIn(
            "effect preflight failed",
            result["error"],
        )
        self.assertIn(
            "escapes workspace",
            result["error"],
        )

    def test_user_cannot_use_constrained_execution(self):
        target = self.test_root / "good.py"
        target.write_text("value = 1\n")

        broker = self._broker(role="user")
        result = broker.bind_central_mind().call(
            "run_python_compile",
            {"paths": [self._relative(target)]},
        )

        self.assertFalse(result["ok"])
        self.assertIn(
            "code.test.execute",
            result["error"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
