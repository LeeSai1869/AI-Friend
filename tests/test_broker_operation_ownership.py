from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path
from types import SimpleNamespace

from section_1_central_mind.mind.broker import ToolBroker


class FakeInventory:
    def __init__(self, items):
        self._items = list(items)

    def all(self):
        return list(self._items)


class BrokerOperationOwnershipTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.tools = self.root / "section_8_tools"
        self.tools.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_tool(
        self,
        folder_name,
        *,
        manifest_name,
        operation_name,
    ):
        folder = self.tools / folder_name
        folder.mkdir(parents=True)

        package = folder / "__init__.py"
        package.write_text("", encoding="utf-8")

        engine = folder / "engine.py"
        engine.write_text(
            textwrap.dedent(
                f"""
                class ExampleTool:
                    name = {operation_name!r}
                    description = "example"
                    parameters = {{}}

                    def __init__(self, workspace_root, broker):
                        self.workspace_root = workspace_root
                        self.broker = broker

                    def call(self, args):
                        return {{
                            "ok": True,
                            "data": "done",
                            "error": None,
                        }}

                TOOLS = [ExampleTool]
                """
            ),
            encoding="utf-8",
        )

        manifest = folder / "__manifest__.py"
        manifest.write_text(
            textwrap.dedent(
                f"""
                ORGAN = {{
                    "name": {manifest_name!r},
                    "kind": "tool",
                    "entry_module": "{folder_name}.engine",
                    "entry_attr": "TOOLS",
                    "security": {{
                        "requires": {{
                            {operation_name!r}: ["workspace.read"],
                        }},
                    }},
                }}
                """
            ),
            encoding="utf-8",
        )

        return folder

    def test_operation_owner_comes_from_inventory_identity(self):
        folder = self._write_tool(
            "filesystem",
            manifest_name="pretend_owner",
            operation_name="read_file",
        )

        inventory = FakeInventory([
            SimpleNamespace(
                name="filesystem",
                kind="tool",
                path=folder,
            )
        ])

        broker = ToolBroker(
            self.root,
            self.tools,
            inventory=inventory,
        )

        self.assertEqual(
            broker.operation_owners["read_file"],
            "filesystem",
        )

    def test_manifest_name_cannot_override_inventory_owner(self):
        folder = self._write_tool(
            "terminal",
            manifest_name="administrator",
            operation_name="run_command",
        )

        inventory = FakeInventory([
            SimpleNamespace(
                name="terminal",
                kind="tool",
                path=folder,
            )
        ])

        broker = ToolBroker(
            self.root,
            self.tools,
            inventory=inventory,
        )

        self.assertEqual(
            broker.operation_owners["run_command"],
            "terminal",
        )
        self.assertNotEqual(
            broker.operation_owners["run_command"],
            "administrator",
        )

    def test_unregistered_tool_folder_is_not_loaded_when_inventory_is_authoritative(self):
        self._write_tool(
            "rogue",
            manifest_name="rogue",
            operation_name="rogue_operation",
        )

        broker = ToolBroker(
            self.root,
            self.tools,
            inventory=FakeInventory([]),
        )

        self.assertNotIn(
            "rogue_operation",
            broker.tools,
        )
        self.assertNotIn(
            "rogue_operation",
            broker.operation_owners,
        )

    def test_inventory_path_must_identify_exactly_one_tool_component(self):
        folder = self._write_tool(
            "filesystem",
            manifest_name="filesystem",
            operation_name="read_file",
        )

        inventory = FakeInventory([
            SimpleNamespace(
                name="first",
                kind="tool",
                path=folder,
            ),
            SimpleNamespace(
                name="second",
                kind="tool",
                path=folder,
            ),
        ])

        broker = ToolBroker(
            self.root,
            self.tools,
            inventory=inventory,
        )

        self.assertNotIn(
            "read_file",
            broker.tools,
        )
        self.assertNotIn(
            "read_file",
            broker.operation_owners,
        )


if __name__ == "__main__":
    unittest.main()
