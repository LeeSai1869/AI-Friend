from __future__ import annotations

import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from types import SimpleNamespace

from section_1_central_mind.guard.contract import GuardPrincipal
from section_1_central_mind.guard.effect_policy import EffectPolicy
from section_1_central_mind.guard.layer import GuardLayer
from section_1_central_mind.guard.policy import GuardPolicy
from section_1_central_mind.mind.broker import ToolBroker



class FakeInventory:
    def __init__(self, infos):
        self._infos = tuple(infos)

    def all(self):
        return self._infos


class BrokerEffectPreflightTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.tools = self.root / "section_8_tools"
        self.tools.mkdir(parents=True)

        for name in (
            "section_1_central_mind",
            "section_2_constitution",
            "section_3_memory",
            "section_9_data",
            "section_10_workspace",
            ".central_mind",
        ):
            (self.root / name).mkdir(exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _principal(self):
        return GuardPrincipal(
            principal_id="user-1",
            kind="human",
            role="user",
            authenticated=True,
            source="test",
        )

    def _guard(self):
        return GuardLayer(
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

    def _write_tool(
        self,
        folder_name,
        *,
        effect_body,
    ):
        folder = self.tools / folder_name
        folder.mkdir()

        (folder / "__init__.py").write_text(
            "",
            encoding="utf-8",
        )

        (folder / "__manifest__.py").write_text(
            textwrap.dedent(
                f"""
                ORGAN = {{
                    "name": {folder_name!r},
                    "kind": "tool",
                    "scope": "outside_guards",
                    "capabilities": ["example_tool"],
                    "security": {{
                        "requires": {{
                            "example_tool": ["workspace.read"]
                        }}
                    }},
                    "entry_module": "{folder_name}.engine",
                    "entry_attr": "TOOLS",
                }}
                """
            ),
            encoding="utf-8",
        )

        (folder / "engine.py").write_text(
            textwrap.dedent(
                f"""
                from section_1_central_mind.guard.contract import ToolEffect

                EXECUTIONS = 0

                class ExampleTool:
                    name = "example_tool"
                    description = "test"
                    parameters = {{}}

                    def __init__(self, workspace_root, broker):
                        self.workspace_root = workspace_root
                        self.broker = broker

                    def effects(self, args):
                        {effect_body}

                    def call(self, args):
                        global EXECUTIONS
                        EXECUTIONS += 1
                        return {{
                            "ok": True,
                            "data": {{"executions": EXECUTIONS}},
                            "error": None,
                        }}

                TOOLS = [ExampleTool]
                """
            ),
            encoding="utf-8",
        )

        return folder

    def _inventory(self, folder):
        return FakeInventory((
            SimpleNamespace(
                name=folder.name,
                kind="tool",
                path=folder,
            ),
        ))

    def test_effects_are_attached_to_single_guard_request(self):
        folder = self._write_tool(
            "effectful",
            effect_body=(
                'return (ToolEffect('
                'action="read", '
                'target=str(self.workspace_root / '
                '"section_10_workspace" / "input.txt"), '
                'scope="exact"),)'
            ),
        )

        guard = self._guard()

        broker = ToolBroker(
            self.root,
            self.tools,
            guard=guard,
            principal=self._principal(),
            inventory=self._inventory(folder),
        )

        result = broker.bind_central_mind().call("example_tool", {})

        self.assertTrue(result["ok"])

        self.assertEqual(
            len(guard.action_audit),
            1,
        )

        request = guard.action_audit[0]["request"]

        self.assertEqual(
            len(request["effects"]),
            1,
        )
        self.assertEqual(
            request["effects"][0]["action"],
            "read",
        )
        self.assertEqual(
            request["effects"][0]["resource"]["kind"],
            "workspace",
        )

    def test_effect_preflight_failure_never_executes_tool(self):
        folder = self._write_tool(
            "broken_effects",
            effect_body='raise RuntimeError("cannot describe effects")',
        )

        broker = ToolBroker(
            self.root,
            self.tools,
            guard=self._guard(),
            principal=self._principal(),
            inventory=self._inventory(folder),
        )

        result = broker.bind_central_mind().call("example_tool", {})

        self.assertFalse(result["ok"])
        self.assertIn(
            "effect preflight failed",
            result["error"],
        )

        module = __import__(
            "broken_effects.engine",
            fromlist=["EXECUTIONS"],
        )

        self.assertEqual(module.EXECUTIONS, 0)
        self.assertEqual(broker.call_count, 0)

    def test_empty_effect_set_never_executes_tool(self):
        folder = self._write_tool(
            "empty_effects",
            effect_body="return ()",
        )

        broker = ToolBroker(
            self.root,
            self.tools,
            guard=self._guard(),
            principal=self._principal(),
            inventory=self._inventory(folder),
        )

        result = broker.bind_central_mind().call("example_tool", {})

        self.assertFalse(result["ok"])
        self.assertIn(
            "declared no effects",
            result["error"],
        )

        module = __import__(
            "empty_effects.engine",
            fromlist=["EXECUTIONS"],
        )

        self.assertEqual(module.EXECUTIONS, 0)
        self.assertEqual(broker.call_count, 0)

    def test_guarded_broker_without_inventory_fails_closed(self):
        folder = self._write_tool(
            "no_inventory",
            effect_body=(
                'return (ToolEffect('
                'action="service", '
                'target="model:test", '
                'scope="service"),)'
            ),
        )

        broker = ToolBroker(
            self.root,
            self.tools,
            guard=self._guard(),
            principal=self._principal(),
        )

        result = broker.bind_central_mind().call("example_tool", {})

        self.assertFalse(result["ok"])
        self.assertIn(
            "requires authoritative Inventory",
            result["error"],
        )

        module = __import__(
            "no_inventory.engine",
            fromlist=["EXECUTIONS"],
        )

        self.assertEqual(module.EXECUTIONS, 0)
        self.assertEqual(broker.call_count, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
