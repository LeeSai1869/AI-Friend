from pathlib import Path
import tempfile
import unittest

from section_1_central_mind.guard.contract import (
    ClassifiedEffect,
    GuardComponent,
    GuardPrincipal,
    GuardRequest,
    ResourceDescriptor,
)
from section_1_central_mind.guard.effect_policy import EffectPolicy
from section_1_central_mind.guard.layer import GuardLayer
from section_1_central_mind.guard.policy import GuardPolicy



class GuardActionAuditTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.policy = GuardPolicy(
            human_role_grants={
                "administrator": {
                    "workspace.read",
                    "workspace.write",
                    "process.execute",
                },
                "trainer": {
                    "workspace.read",
                    "knowledge.propose",
                },
                "user": {
                    "workspace.read",
                },
            },
            internal_grants={
                "central_mind": {
                    "workspace.read",
                },
            },
        )

        self.guards = GuardLayer(
            self.root,
            policy=self.policy,
            effect_policy=EffectPolicy(
                resource_rules={
                    "workspace": {
                        "read": {"exact"},
                    },
                },
                semantic_rules={
                    "memory": {"service"},
                },
            ),
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _request(
        self,
        *,
        principal=None,
        component=None,
        operation="read",
        resource="workspace.file",
        target="workspace/example.txt",
        required=("workspace.read",),
        effects=None,
    ):
        if effects is None:
            effects = (
                ClassifiedEffect(
                    action="read",
                    scope="exact",
                    resource=ResourceDescriptor(
                        kind="workspace",
                        path=self.root / "example.txt",
                        relative_path="example.txt",
                    ),
                ),
            )

        return GuardRequest(
            principal=principal or GuardPrincipal(
                principal_id="central_mind",
                kind="internal",
                source="runtime",
            ),
            component=component or GuardComponent(
                kind="tool",
                name="read_file",
            ),
            operation=operation,
            resource=resource,
            target=target,
            required_capabilities=tuple(required),
            effects=tuple(effects),
        )

    def test_malformed_request_is_blocked(self):
        verdict = self.guards.audit_action({
            "operation": "read",
        })

        self.assertEqual(verdict["verdict"], "BLOCK")
        self.assertIn("Malformed", verdict["reason"])

    def test_malformed_request_is_audited(self):
        self.guards.audit_action(None)

        self.assertEqual(len(self.guards.action_audit), 1)
        self.assertIsNone(
            self.guards.action_audit[0]["request"]
        )

    def test_unauthenticated_human_is_blocked(self):
        request = self._request(
            principal=GuardPrincipal(
                principal_id="user.example",
                kind="human",
                role="user",
                authenticated=False,
                source="auth_service",
            )
        )

        verdict = self.guards.audit_action(request)

        self.assertEqual(verdict["verdict"], "BLOCK")
        self.assertIn(
            "not authenticated",
            verdict["reason"],
        )

    def test_authenticated_user_with_grant_passes(self):
        request = self._request(
            principal=GuardPrincipal(
                principal_id="user.example",
                kind="human",
                role="user",
                authenticated=True,
                source="auth_service",
            ),
            required=("workspace.read",),
        )

        verdict = self.guards.audit_action(request)

        self.assertEqual(verdict["verdict"], "PASS")

    def test_authenticated_user_without_grant_is_blocked(self):
        request = self._request(
            principal=GuardPrincipal(
                principal_id="user.example",
                kind="human",
                role="user",
                authenticated=True,
                source="auth_service",
            ),
            operation="execute",
            resource="process",
            required=("process.execute",),
        )

        verdict = self.guards.audit_action(request)

        self.assertEqual(verdict["verdict"], "BLOCK")
        self.assertEqual(
            verdict["missing_capabilities"],
            ["process.execute"],
        )

    def test_admin_still_needs_declared_requirement(self):
        request = self._request(
            principal=GuardPrincipal(
                principal_id="admin.example",
                kind="human",
                role="administrator",
                authenticated=True,
                source="auth_service",
            ),
            required=(),
        )

        verdict = self.guards.audit_action(request)

        self.assertEqual(verdict["verdict"], "BLOCK")
        self.assertIn(
            "no required security capability",
            verdict["reason"],
        )

    def test_internal_identity_uses_only_internal_grants(self):
        request = self._request(
            principal=GuardPrincipal(
                principal_id="central_mind",
                kind="internal",
                role="administrator",
                authenticated=False,
                source="runtime",
            ),
            operation="execute",
            resource="process",
            required=("process.execute",),
        )

        verdict = self.guards.audit_action(request)

        self.assertEqual(verdict["verdict"], "BLOCK")

    def test_internal_granted_capability_passes(self):
        request = self._request(
            principal=GuardPrincipal(
                principal_id="central_mind",
                kind="internal",
                source="runtime",
            ),
            required=("workspace.read",),
        )

        verdict = self.guards.audit_action(request)

        self.assertEqual(verdict["verdict"], "PASS")

    def test_unknown_future_tool_does_not_gain_authority_from_name(self):
        request = self._request(
            principal=GuardPrincipal(
                principal_id="user.example",
                kind="human",
                role="user",
                authenticated=True,
                source="auth_service",
            ),
            component=GuardComponent(
                kind="tool",
                name="future_tool_100",
            ),
            operation="execute",
            resource="process",
            required=("process.execute",),
        )

        verdict = self.guards.audit_action(request)

        self.assertEqual(verdict["verdict"], "BLOCK")

    def test_multiple_required_capabilities_all_must_pass(self):
        request = self._request(
            principal=GuardPrincipal(
                principal_id="trainer.example",
                kind="human",
                role="trainer",
                authenticated=True,
                source="auth_service",
            ),
            operation="propose",
            resource="knowledge",
            required=(
                "workspace.read",
                "knowledge.propose",
            ),
            effects=(
                ClassifiedEffect(
                    action="memory",
                    scope="service",
                    target="memory:knowledge_proposal",
                ),
            ),
        )

        verdict = self.guards.audit_action(request)

        self.assertEqual(verdict["verdict"], "PASS")

    def test_required_capabilities_are_in_audit_record(self):
        request = self._request(
            required=("workspace.read",),
        )

        self.guards.audit_action(request)

        entry = self.guards.action_audit[-1]

        self.assertEqual(
            entry["request"]["required_capabilities"],
            ["workspace.read"],
        )

    def test_every_attempt_produces_exactly_one_audit_entry(self):
        self.guards.audit_action(
            self._request(required=("workspace.read",))
        )
        self.guards.audit_action(
            self._request(
                operation="write",
                required=("workspace.write",),
            )
        )
        self.guards.audit_action(
            self._request(
                operation="execute",
                required=("process.execute",),
            )
        )

        self.assertEqual(
            len(self.guards.action_audit),
            3,
        )


if __name__ == "__main__":
    unittest.main()
