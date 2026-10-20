import unittest

from section_1_central_mind.guard.contract import (
    GuardComponent,
    GuardPrincipal,
    GuardRequest,
)


class GuardContractTests(unittest.TestCase):

    def test_human_request_can_be_constructed(self):
        principal = GuardPrincipal(
            principal_id="akbar.jhanzeeb",
            kind="human",
            role="administrator",
            authenticated=True,
            source="auth_service",
        )

        component = GuardComponent(
            kind="tool",
            name="read_file",
        )

        request = GuardRequest(
            principal=principal,
            component=component,
            operation="read",
            resource="workspace.file",
            target="section_10_workspace/example.txt",
            scope="workspace",
            metadata={"reason": "inspect"},
        )

        self.assertEqual(request.principal.role, "administrator")
        self.assertEqual(request.component.name, "read_file")
        self.assertEqual(request.operation, "read")
        self.assertTrue(request.action_id.startswith("act_"))

    def test_internal_component_is_not_automatically_human(self):
        principal = GuardPrincipal(
            principal_id="central_mind",
            kind="internal",
            role="",
            authenticated=False,
            source="runtime",
        )

        self.assertEqual(principal.kind, "internal")
        self.assertNotEqual(principal.kind, "human")
        self.assertFalse(principal.authenticated)

    def test_invalid_principal_kind_fails_closed(self):
        with self.assertRaises(ValueError):
            GuardPrincipal(
                principal_id="someone",
                kind="administrator",
                role="administrator",
                authenticated=True,
            )

    def test_invalid_component_kind_fails_closed(self):
        with self.assertRaises(ValueError):
            GuardComponent(
                kind="magic_plugin",
                name="example",
            )

    def test_operation_is_required(self):
        principal = GuardPrincipal(
            principal_id="central_mind",
            kind="internal",
        )
        component = GuardComponent(
            kind="tool",
            name="example",
        )

        with self.assertRaises(ValueError):
            GuardRequest(
                principal=principal,
                component=component,
                operation="",
                resource="workspace.file",
            )

    def test_resource_is_required(self):
        principal = GuardPrincipal(
            principal_id="central_mind",
            kind="internal",
        )
        component = GuardComponent(
            kind="tool",
            name="example",
        )

        with self.assertRaises(ValueError):
            GuardRequest(
                principal=principal,
                component=component,
                operation="read",
                resource="",
            )

    def test_metadata_is_copied_from_caller(self):
        metadata = {"value": "before"}

        request = GuardRequest(
            principal=GuardPrincipal(
                principal_id="central_mind",
                kind="internal",
            ),
            component=GuardComponent(
                kind="tool",
                name="example",
            ),
            operation="read",
            resource="workspace.file",
            metadata=metadata,
        )

        metadata["value"] = "after"

        self.assertEqual(
            request.metadata["value"],
            "before",
        )

    def test_audit_dict_contains_complete_identity_chain(self):
        request = GuardRequest(
            principal=GuardPrincipal(
                principal_id="teach.jhanzeeb",
                kind="human",
                role="trainer",
                authenticated=True,
                source="auth_service",
            ),
            component=GuardComponent(
                kind="domain",
                name="languages",
            ),
            operation="invoke",
            resource="domain",
            target="languages",
        )

        record = request.to_audit_dict()

        self.assertEqual(
            record["principal"]["principal_id"],
            "teach.jhanzeeb",
        )
        self.assertEqual(
            record["principal"]["role"],
            "trainer",
        )
        self.assertEqual(
            record["component"]["kind"],
            "domain",
        )
        self.assertEqual(
            record["component"]["name"],
            "languages",
        )
        self.assertEqual(record["operation"], "invoke")


if __name__ == "__main__":
    unittest.main()
