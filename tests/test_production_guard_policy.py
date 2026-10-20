from __future__ import annotations

import unittest

from section_1_central_mind.guard.contract import GuardPrincipal
from section_1_central_mind.guard.production_policy import (
    build_production_guard_policy,
)


class ProductionGuardPolicyTests(unittest.TestCase):

    def setUp(self):
        self.policy = build_production_guard_policy()

    def human(self, role: str, *, authenticated: bool = True):
        return GuardPrincipal(
            principal_id=f"{role}-account",
            kind="human",
            role=role,
            authenticated=authenticated,
            source="auth_service",
        )

    def internal(self, name: str = "central_mind"):
        return GuardPrincipal(
            principal_id=name,
            kind="internal",
            role="",
            authenticated=True,
            source="runtime",
        )

    def assertAllowed(self, principal, *capabilities):
        decision = self.policy.evaluate(principal, capabilities)
        self.assertTrue(decision.allowed, decision.reason)

    def assertDenied(self, principal, *capabilities):
        decision = self.policy.evaluate(principal, capabilities)
        self.assertFalse(decision.allowed)

    def test_administrator_current_grants(self):
        admin = self.human("administrator")
        self.assertAllowed(admin, "workspace.read")
        self.assertAllowed(admin, "network.access")
        self.assertDenied(admin, "workspace.write")
        self.assertDenied(admin, "knowledge.propose")
        self.assertDenied(admin, "process.execute")

    def test_trainer_current_grants(self):
        trainer = self.human("trainer")
        self.assertAllowed(trainer, "workspace.read")
        self.assertAllowed(trainer, "workspace.write")
        self.assertAllowed(trainer, "knowledge.propose")
        self.assertAllowed(trainer, "network.access")
        self.assertDenied(trainer, "process.execute")

    def test_ordinary_user_current_grants(self):
        user = self.human("user")
        self.assertAllowed(user, "workspace.read")
        self.assertAllowed(user, "network.access")
        self.assertDenied(user, "workspace.write")
        self.assertDenied(user, "knowledge.propose")
        self.assertDenied(user, "process.execute")

    def test_new_capability_is_denied_until_explicitly_granted(self):
        for role in ("administrator", "trainer", "user"):
            with self.subTest(role=role):
                self.assertDenied(
                    self.human(role),
                    "future.seventh_capability",
                )

    def test_capability_vocabulary_is_not_fixed_to_current_five(self):
        # GuardPolicy itself accepts a future capability syntactically.
        # Production denies it because no trusted grant exists.
        decision = self.policy.evaluate(
            self.human("trainer"),
            {"image.generate"},
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(
            decision.missing,
            frozenset({"image.generate"}),
        )

    def test_process_execute_is_ungranted_to_every_human_role(self):
        for role in ("administrator", "trainer", "user"):
            with self.subTest(role=role):
                self.assertDenied(
                    self.human(role),
                    "process.execute",
                )

    def test_unauthenticated_human_has_no_authority(self):
        self.assertDenied(
            self.human("trainer", authenticated=False),
            "workspace.read",
        )

    def test_unknown_human_role_has_no_authority(self):
        self.assertDenied(
            self.human("invented-role"),
            "workspace.read",
        )

    def test_internal_identity_has_no_implicit_production_grants(self):
        self.assertDenied(
            self.internal(),
            "workspace.read",
        )
        self.assertDenied(
            self.internal(),
            "network.access",
        )

    def test_multiple_requirements_require_all_grants(self):
        trainer = self.human("trainer")
        self.assertAllowed(
            trainer,
            "workspace.read",
            "knowledge.propose",
        )

        user = self.human("user")
        self.assertDenied(
            user,
            "workspace.read",
            "knowledge.propose",
        )


if __name__ == "__main__":
    unittest.main()
