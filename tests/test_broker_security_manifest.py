from pathlib import Path
import tempfile
import textwrap
import unittest
from types import SimpleNamespace

from section_1_central_mind.mind.broker import ToolBroker
from section_1_central_mind.guard.contract import (
    GuardPrincipal,
    ToolEffect,
)
from section_1_central_mind.guard.layer import GuardLayer
from section_1_central_mind.guard.policy import GuardPolicy
from section_1_central_mind.guard.effect_policy import EffectPolicy


class FakeInventory:
    def __init__(self, infos):
        self._infos = tuple(infos)

    def all(self):
        return self._infos


class BrokerSecurityManifestTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.tools = self.root / "tools"
        self.tools.mkdir()
        self.logs = []

    def tearDown(self):
        self.tmp.cleanup()

    def _make_tool_package(
        self,
        folder_name,
        *,
        tool_name="example_tool",
        security_text=None,
    ):
        folder = self.tools / folder_name
        folder.mkdir()

        (folder / "__init__.py").write_text(
            "",
            encoding="utf-8",
        )

        (folder / "engine.py").write_text(
            textwrap.dedent(
                f"""
                from section_1_central_mind.guard.contract import ToolEffect

                class ExampleTool:
                    name = {tool_name!r}
                    description = "example"
                    parameters = {{}}

                    def __init__(self, workspace_root, broker):
                        self.workspace_root = workspace_root
                        self.broker = broker

                    def effects(self, args):
                        return (
                            ToolEffect(
                                action="read",
                                target=str(self.workspace_root),
                                scope="exact",
                            ),
                        )

                    def call(self, args):
                        return {{
                            "ok": True,
                            "data": args,
                            "error": None,
                        }}

                TOOLS = [ExampleTool]
                """
            ),
            encoding="utf-8",
        )

        security_line = (
            f'    "security": {security_text},\n'
            if security_text is not None
            else ""
        )

        (folder / "__manifest__.py").write_text(
            (
                "ORGAN = {\n"
                f'    "name": {folder_name!r},\n'
                '    "kind": "tool",\n'
                '    "scope": "outside_guards",\n'
                f'    "capabilities": [{tool_name!r}],\n'
                f"{security_line}"
                f'    "entry_module": "{folder_name}.engine",\n'
                '    "entry_attr": "TOOLS",\n'
                "}\n"
            ),
            encoding="utf-8",
        )

    def _broker(self):
        return ToolBroker(
            workspace_root=self.root,
            tools_dir=self.tools,
            logger=self.logs.append,
        )

    def _guarded_broker(self):
        principal = GuardPrincipal(
            principal_id="manifest-test-user",
            kind="human",
            role="user",
            authenticated=True,
            source="test",
        )

        guard = GuardLayer(
            self.root,
            policy=GuardPolicy(
                human_role_grants={
                    "user": {
                        "workspace.read",
                    },
                },
            ),
            effect_policy=EffectPolicy(
                resource_rules={
                    "workspace": {
                        "read": {"exact"},
                    },
                },
            ),
        )

        folder = self.tools / "delta"
        inventory = FakeInventory((
            SimpleNamespace(
                name=folder.name,
                kind="tool",
                path=folder,
            ),
        ))

        return ToolBroker(
            workspace_root=self.root,
            tools_dir=self.tools,
            logger=self.logs.append,
            guard=guard,
            principal=principal,
            inventory=inventory,
        )

    def test_security_requirements_are_registered(self):
        self._make_tool_package(
            "alpha",
            security_text=(
                '{"requires": {'
                '"example_tool": ["workspace.read"]'
                '}}'
            ),
        )

        broker = self._broker()

        self.assertIn("example_tool", broker.tools)
        self.assertEqual(
            broker.security_requirements["example_tool"],
            ("workspace.read",),
        )

    def test_requirements_are_normalized(self):
        self._make_tool_package(
            "beta",
            security_text=(
                '{"requires": {'
                '"example_tool": '
                '[" WORKSPACE.READ ", "Network.Access"]'
                '}}'
            ),
        )

        broker = self._broker()

        self.assertEqual(
            broker.security_requirements["example_tool"],
            (
                "workspace.read",
                "network.access",
            ),
        )

    def test_missing_security_declaration_is_empty_for_transition(self):
        self._make_tool_package("gamma")

        broker = self._broker()

        self.assertIn("example_tool", broker.tools)
        self.assertEqual(
            broker.security_requirements["example_tool"],
            (),
        )

    def test_model_call_args_cannot_override_requirements(self):
        self._make_tool_package(
            "delta",
            security_text=(
                '{"requires": {'
                '"example_tool": ["workspace.read"]'
                '}}'
            ),
        )

        broker = self._guarded_broker()

        result = broker.bind_central_mind().call(
            "example_tool",
            {
                "requires": ["process.execute"],
                "security": {
                    "requires": ["process.execute"]
                },
            },
        )

        self.assertTrue(result["ok"])
        self.assertEqual(
            broker.security_requirements["example_tool"],
            ("workspace.read",),
        )
        self.assertEqual(
            result["data"]["requires"],
            ["process.execute"],
        )
        self.assertEqual(
            result["data"]["security"]["requires"],
            ["process.execute"],
        )

    def test_invalid_security_manifest_fails_registration_closed(self):
        self._make_tool_package(
            "epsilon",
            security_text=(
                '{"requires": {'
                '"example_tool": "workspace.read"'
                '}}'
            ),
        )

        broker = self._broker()

        self.assertNotIn("example_tool", broker.tools)
        self.assertNotIn(
            "example_tool",
            broker.security_requirements,
        )

    def test_duplicate_tool_name_does_not_replace_first_registration(self):
        self._make_tool_package(
            "first",
            security_text=(
                '{"requires": {'
                '"example_tool": ["workspace.read"]'
                '}}'
            ),
        )

        self._make_tool_package(
            "second",
            security_text=(
                '{"requires": {'
                '"example_tool": ["process.execute"]'
                '}}'
            ),
        )

        broker = self._broker()

        self.assertEqual(
            broker.security_requirements["example_tool"],
            ("workspace.read",),
        )

    def test_requirement_for_nonexistent_tool_is_not_registered(self):
        self._make_tool_package(
            "zeta",
            security_text=(
                '{"requires": {'
                '"not_exported": ["workspace.write"]'
                '}}'
            ),
        )

        broker = self._broker()

        self.assertIn("example_tool", broker.tools)
        self.assertNotIn(
            "not_exported",
            broker.security_requirements,
        )

        self.assertTrue(
            any(
                "unregistered tool: not_exported" in log
                for log in self.logs
            )
        )


if __name__ == "__main__":
    unittest.main()
