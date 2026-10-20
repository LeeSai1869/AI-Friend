import unittest

from section_1_central_mind.guard.contract import GuardPrincipal
from section_1_central_mind.guard.policy import GuardPolicy


class GuardPolicyTests(unittest.TestCase):

    def setUp(self):
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
                "verifier": {
                    "workspace.read",
                    "verification.run",
                },
            },
        )

    def _human(self, role, authenticated=True):
        return GuardPrincipal(
            principal_id=f"{role}.example",
            kind="human",
            role=role,
            authenticated=authenticated,
            source="auth_service",
        )

    def test_exact_capability_grant_passes(self):
        decision = self.policy.evaluate(
            self._human("trainer"),
            {"knowledge.propose"},
        )

        self.assertTrue(decision.allowed)
        self.assertFalse(decision.missing)

    def test_missing_capability_fails_closed(self):
        decision = self.policy.evaluate(
            self._human("trainer"),
            {"process.execute"},
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(
            decision.missing,
            frozenset({"process.execute"}),
        )

    def test_multiple_requirements_all_must_be_granted(self):
        decision = self.policy.evaluate(
            self._human("trainer"),
            {
                "workspace.read",
                "knowledge.propose",
            },
        )

        self.assertTrue(decision.allowed)

    def test_one_missing_requirement_blocks_entire_action(self):
        decision = self.policy.evaluate(
            self._human("trainer"),
            {
                "workspace.read",
                "process.execute",
            },
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(
            decision.missing,
            frozenset({"process.execute"}),
        )

    def test_unauthenticated_human_gets_no_grants(self):
        decision = self.policy.evaluate(
            self._human(
                "administrator",
                authenticated=False,
            ),
            {"workspace.read"},
        )

        self.assertFalse(decision.allowed)
        self.assertFalse(decision.granted)

    def test_role_string_not_in_policy_grants_nothing(self):
        decision = self.policy.evaluate(
            self._human("super_admin"),
            {"workspace.read"},
        )

        self.assertFalse(decision.allowed)
        self.assertFalse(decision.granted)

    def test_internal_identity_uses_separate_grants(self):
        principal = GuardPrincipal(
            principal_id="verifier",
            kind="internal",
            source="runtime",
        )

        decision = self.policy.evaluate(
            principal,
            {"verification.run"},
        )

        self.assertTrue(decision.allowed)

    def test_internal_component_cannot_claim_human_role_grants(self):
        principal = GuardPrincipal(
            principal_id="central_mind",
            kind="internal",
            role="administrator",
            authenticated=False,
            source="runtime",
        )

        decision = self.policy.evaluate(
            principal,
            {"process.execute"},
        )

        self.assertFalse(decision.allowed)

    def test_unknown_internal_identity_gets_no_grants(self):
        principal = GuardPrincipal(
            principal_id="future_agent",
            kind="internal",
            source="runtime",
        )

        decision = self.policy.evaluate(
            principal,
            {"workspace.read"},
        )

        self.assertFalse(decision.allowed)

    def test_empty_requirements_do_not_mean_allow(self):
        decision = self.policy.evaluate(
            self._human("administrator"),
            set(),
        )

        self.assertFalse(decision.allowed)
        self.assertIn(
            "no required security capability",
            decision.reason,
        )

    def test_invalid_capability_fails_closed(self):
        decision = self.policy.evaluate(
            self._human("administrator"),
            {"workspace read"},
        )

        self.assertFalse(decision.allowed)
        self.assertIn(
            "invalid capability",
            decision.reason,
        )

    def test_capability_names_are_normalized(self):
        decision = self.policy.evaluate(
            self._human("administrator"),
            {" WORKSPACE.READ "},
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(
            decision.required,
            frozenset({"workspace.read"}),
        )


if __name__ == "__main__":
    unittest.main()
