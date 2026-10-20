from pathlib import Path
import tempfile
import unittest

from section_1_central_mind.guard.contract import (
    ClassifiedEffect,
    GuardComponent,
    GuardPrincipal,
    GuardRequest,
)
from section_1_central_mind.guard.effect_policy import EffectPolicy
from section_1_central_mind.guard.layer import GuardLayer
from section_1_central_mind.guard.policy import GuardPolicy
from section_1_central_mind.guard.resources import ResourceDescriptor


class _Memory:
    def search(self, *args, **kwargs):
        return []


class GuardEffectIntegrationTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()

        (self.root / "section_0_central_mind").mkdir(
            parents=True
        )

        self.capability_policy = GuardPolicy(
            internal_grants={
                "central_mind": {
                    "workspace.read",
                    "workspace.write",
                },
            },
        )

        self.effect_policy = EffectPolicy(
            resource_rules={
                "workspace": {
                    "read": {"exact"},
                },
            },
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _chain(self):
        return (
            GuardComponent(
                kind="central_mind",
                name="central_mind",
            ),
            GuardComponent(
                kind="tool",
                name="filesystem",
            ),
        )

    def _principal(self):
        return GuardPrincipal(
            principal_id="central_mind",
            kind="internal",
            source="runtime",
        )

    def _workspace_effect(self, action="read"):
        return ClassifiedEffect(
            action=action,
            scope="exact",
            resource=ResourceDescriptor(
                kind="workspace",
                path=self.root / "example.txt",
                relative_path="example.txt",
            ),
        )

    def _request(
        self,
        *,
        required=("workspace.read",),
        effects=None,
    ):
        values = {
            "principal": self._principal(),
            "component": self._chain()[-1],
            "component_chain": self._chain(),
            "operation": "read_file",
            "resource": "tool",
            "target": "read_file",
            "required_capabilities": tuple(required),
        }

        if effects is not None:
            values["effects"] = tuple(effects)

        return GuardRequest(**values)

    def _guard(self, *, effect_policy=True):
        return GuardLayer(
            self.root,
            policy=self.capability_policy,
            effect_policy=(
                self.effect_policy
                if effect_policy
                else None
            ),
        )

    def test_both_gates_pass(self):
        guard = self._guard()

        verdict = guard.audit_action(
            self._request(
                effects=(self._workspace_effect(),),
            )
        )

        self.assertEqual(verdict["verdict"], "PASS")
        self.assertEqual(
            [c["name"] for c in verdict["checks"]],
            [
                "request_contract",
                "explicit_policy",
                "effect_policy",
            ],
        )
        self.assertTrue(verdict["checks"][-1]["passed"])
        self.assertEqual(len(guard.action_audit), 1)

    def test_capability_gate_failure_blocks_before_effect_gate(self):
        guard = self._guard()

        verdict = guard.audit_action(
            self._request(
                required=("process.execute",),
                effects=(self._workspace_effect(),),
            )
        )

        self.assertEqual(verdict["verdict"], "BLOCK")
        self.assertEqual(
            verdict["missing_capabilities"],
            ["process.execute"],
        )
        self.assertEqual(
            [c["name"] for c in verdict["checks"]],
            [
                "request_contract",
                "explicit_policy",
            ],
        )
        self.assertEqual(len(guard.action_audit), 1)

    def test_effect_gate_failure_blocks(self):
        guard = self._guard()

        verdict = guard.audit_action(
            self._request(
                effects=(
                    self._workspace_effect(
                        action="write",
                    ),
                ),
            )
        )

        self.assertEqual(verdict["verdict"], "BLOCK")
        self.assertFalse(verdict["checks"][-1]["passed"])
        self.assertEqual(
            verdict["checks"][-1]["name"],
            "effect_policy",
        )
        self.assertEqual(
            verdict["denied_effect_index"],
            0,
        )
        self.assertEqual(len(guard.action_audit), 1)

    def test_enabled_effect_policy_blocks_empty_effects(self):
        guard = self._guard()

        verdict = guard.audit_action(
            self._request()
        )

        self.assertEqual(verdict["verdict"], "BLOCK")
        self.assertIn(
            "no classified effects",
            verdict["reason"],
        )
        self.assertEqual(
            verdict["checks"][-1],
            {
                "name": "effect_policy",
                "passed": False,
            },
        )
        self.assertEqual(len(guard.action_audit), 1)

    def test_missing_effect_policy_fails_closed(self):
        guard = self._guard(effect_policy=False)

        verdict = guard.audit_action(
            self._request()
        )

        self.assertEqual(verdict["verdict"], "BLOCK")
        self.assertEqual(
            verdict["reason"],
            "Effect authorization policy is not configured.",
        )
        self.assertEqual(
            [c["name"] for c in verdict["checks"]],
            [
                "request_contract",
                "explicit_policy",
                "effect_policy",
            ],
        )
        self.assertEqual(len(guard.action_audit), 1)


if __name__ == "__main__":
    unittest.main()
