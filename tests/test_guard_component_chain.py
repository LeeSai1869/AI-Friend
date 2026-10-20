from __future__ import annotations

import unittest

from section_1_central_mind.guard.contract import (
    GuardComponent,
    GuardPrincipal,
    GuardRequest,
)


class GuardComponentChainTests(unittest.TestCase):

    def _principal(self):
        return GuardPrincipal(
            principal_id="user.example",
            kind="human",
            role="user",
            authenticated=True,
            source="auth_service",
        )

    def test_trusted_execution_chain_can_be_recorded(self):
        mind = GuardComponent(
            kind="central_mind",
            name="central_mind",
        )
        coder = GuardComponent(
            kind="domain",
            name="coder",
        )
        filesystem = GuardComponent(
            kind="tool",
            name="filesystem",
        )

        request = GuardRequest(
            principal=self._principal(),
            component=filesystem,
            component_chain=(
                mind,
                coder,
                filesystem,
            ),
            operation="read",
            resource="workspace.file",
            target="section_10_workspace/example.py",
            required_capabilities=("workspace.read",),
        )

        self.assertEqual(
            request.component_chain,
            (mind, coder, filesystem),
        )
        self.assertEqual(
            request.component,
            filesystem,
        )

    def test_chain_must_end_with_current_component(self):
        mind = GuardComponent(
            kind="central_mind",
            name="central_mind",
        )
        coder = GuardComponent(
            kind="domain",
            name="coder",
        )
        filesystem = GuardComponent(
            kind="tool",
            name="filesystem",
        )

        with self.assertRaises(ValueError):
            GuardRequest(
                principal=self._principal(),
                component=filesystem,
                component_chain=(mind, coder),
                operation="read",
                resource="workspace.file",
                required_capabilities=("workspace.read",),
            )

    def test_chain_members_must_be_guard_components(self):
        filesystem = GuardComponent(
            kind="tool",
            name="filesystem",
        )

        with self.assertRaises(ValueError):
            GuardRequest(
                principal=self._principal(),
                component=filesystem,
                component_chain=(
                    "central_mind",
                    filesystem,
                ),
                operation="read",
                resource="workspace.file",
                required_capabilities=("workspace.read",),
            )

    def test_chain_must_be_immutable_tuple(self):
        filesystem = GuardComponent(
            kind="tool",
            name="filesystem",
        )

        with self.assertRaises(ValueError):
            GuardRequest(
                principal=self._principal(),
                component=filesystem,
                component_chain=[filesystem],
                operation="read",
                resource="workspace.file",
                required_capabilities=("workspace.read",),
            )

    def test_audit_record_preserves_principal_and_execution_chain(self):
        mind = GuardComponent(
            kind="central_mind",
            name="central_mind",
        )
        coder = GuardComponent(
            kind="domain",
            name="coder",
        )
        filesystem = GuardComponent(
            kind="tool",
            name="filesystem",
        )

        request = GuardRequest(
            principal=self._principal(),
            component=filesystem,
            component_chain=(
                mind,
                coder,
                filesystem,
            ),
            operation="read",
            resource="workspace.file",
            required_capabilities=("workspace.read",),
        )

        record = request.to_audit_dict()

        self.assertEqual(
            record["principal"]["principal_id"],
            "user.example",
        )
        self.assertEqual(
            record["component_chain"],
            [
                {
                    "kind": "central_mind",
                    "name": "central_mind",
                },
                {
                    "kind": "domain",
                    "name": "coder",
                },
                {
                    "kind": "tool",
                    "name": "filesystem",
                },
            ],
        )

    def test_empty_chain_remains_temporarily_compatible(self):
        filesystem = GuardComponent(
            kind="tool",
            name="filesystem",
        )

        request = GuardRequest(
            principal=self._principal(),
            component=filesystem,
            operation="read",
            resource="workspace.file",
            required_capabilities=("workspace.read",),
        )

        self.assertEqual(request.component_chain, ())


if __name__ == "__main__":
    unittest.main()
