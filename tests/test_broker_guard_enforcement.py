from pathlib import Path
import shutil
import sys
import tempfile
import textwrap
import unittest

from section_1_central_mind.guard.contract import GuardPrincipal
from section_1_central_mind.guard.effect_policy import EffectPolicy
from section_1_central_mind.guard.layer import GuardLayer
from section_1_central_mind.guard.policy import GuardPolicy
from section_1_central_mind.guard.production_policy import (
    build_production_effect_policy,
)
from section_1_central_mind.mind.broker import ToolBroker



class _Inventory:
    def __init__(self, items):
        self._items = tuple(items)

    def all(self):
        return self._items


class BrokerGuardEnforcementTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.tools = self.root / "tools"
        self.tools.mkdir()

        (self.root / "section_0_central_mind").mkdir()

        # ToolBroker imports discovered tools through normal Python
        # module imports. A unique package name per test prevents
        # sys.modules from reusing a synthetic module created by an
        # earlier test case.
        self.package_name = (
            "counting_"
            + self._testMethodName.replace("-", "_")
        )

        # The real-filesystem integration fixture uses the production
        # top-level package name ``filesystem``. Other Broker tests may
        # already have cached a different temporary package with that
        # same name. Preserve that incoming state so this test can
        # isolate itself without changing module state for later tests.
        self._filesystem_modules_before = {
            name: module
            for name, module in sys.modules.items()
            if name == "filesystem"
            or name.startswith("filesystem.")
        }

    def tearDown(self):
        # Remove any filesystem modules imported by this test, then put
        # back exactly the module objects that existed on entry.
        for name in tuple(sys.modules):
            if name == "filesystem" or name.startswith("filesystem."):
                sys.modules.pop(name, None)

        sys.modules.update(self._filesystem_modules_before)
        self.tmp.cleanup()

    def _make_counting_tool(
        self,
        *,
        requirement="workspace.read",
    ):
        folder = self.tools / self.package_name
        folder.mkdir()

        (folder / "__init__.py").write_text(
            "",
            encoding="utf-8",
        )

        (folder / "engine.py").write_text(
            textwrap.dedent(
                """
                from section_1_central_mind.guard.contract import ToolEffect

                EXECUTIONS = 0

                class CountingTool:
                    name = "counting_tool"
                    description = "counts executions"
                    parameters = {}

                    def __init__(self, workspace_root, broker):
                        self.workspace_root = workspace_root
                        self.broker = broker

                    def effects(self, args):
                        return (
                            ToolEffect(
                                action="read",
                                target=str(
                                    self.workspace_root
                                    / "guard-test-input.txt"
                                ),
                                scope="exact",
                            ),
                        )

                    def call(self, args):
                        global EXECUTIONS
                        EXECUTIONS += 1
                        return {
                            "ok": True,
                            "data": {
                                "executions": EXECUTIONS,
                            },
                            "error": None,
                        }

                TOOLS = [CountingTool]
                """
            ),
            encoding="utf-8",
        )

        (folder / "__manifest__.py").write_text(
            textwrap.dedent(
                f"""
                ORGAN = {{
                    "name": {self.package_name!r},
                    "kind": "tool",
                    "scope": "outside_guards",
                    "capabilities": ["counting_tool"],
                    "security": {{
                        "requires": {{
                            "counting_tool": [{requirement!r}],
                        }},
                    }},
                    "entry_module": {self.package_name + ".engine"!r},
                    "entry_attr": "TOOLS",
                }}
                """
            ),
            encoding="utf-8",
        )

        return folder

    def _inventory_for(self, folder):
        from types import SimpleNamespace

        return _Inventory((
            SimpleNamespace(
                name=folder.name,
                kind="tool",
                path=folder,
            ),
        ))

    def _principal(self, role="user"):
        return GuardPrincipal(
            principal_id=f"{role}.example",
            kind="human",
            role=role,
            authenticated=True,
            source="auth_service",
        )

    def _guard(self, grants):
        policy = GuardPolicy(
            human_role_grants=grants,
        )

        return GuardLayer(
            self.root,
            policy=policy,
            effect_policy=EffectPolicy(
                resource_rules={
                    "workspace": {
                        "read": {"exact"},
                    },
                },
            ),
        )

    def _make_real_filesystem_tool(self):
        """Install the real filesystem tool with its shared base dependency."""

        # This fixture intentionally needs its own copied production
        # ``filesystem`` package. Remove any same-named package cached
        # by an earlier test before ToolBroker performs normal imports.
        for name in tuple(sys.modules):
            if name == "filesystem" or name.startswith("filesystem."):
                sys.modules.pop(name, None)

        project_tools = (
            Path(__file__).resolve().parents[1]
            / "section_8_tools"
        )

        # Reproduce the production package layout needed by the real tool:
        #
        #   tools/
        #       _base/
        #       filesystem/
        #
        # The filesystem implementation imports shared infrastructure from
        # the sibling ``_base`` package, so copying filesystem alone is not
        # a valid production-equivalent fixture.
        shutil.copytree(
            project_tools / "_base",
            self.tools / "_base",
        )

        folder = self.tools / "filesystem"
        shutil.copytree(
            project_tools / "filesystem",
            folder,
        )

        return folder

    def _production_effect_guard(self):
        return GuardLayer(
            self.root,
            policy=GuardPolicy(
                human_role_grants={
                    "trainer": {
                        "workspace.read",
                        "workspace.write",
                    },
                },
            ),
            effect_policy=build_production_effect_policy(),
        )

    def _assert_real_write_denied_before_execution(self, relative_path):
        folder = self._make_real_filesystem_tool()

        target = self.root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)

        original = "ORIGINAL-CONTENT"
        target.write_text(original, encoding="utf-8")

        broker = ToolBroker(
            self.root,
            self.tools,
            guard=self._production_effect_guard(),
            principal=self._principal("trainer"),
            inventory=self._inventory_for(folder),
        )

        result = broker.bind_central_mind().call(
            "write_file",
            {
                "path": relative_path,
                "content": "MUTATED-BY-TOOL",
            },
        )

        self.assertFalse(result["ok"], result)
        self.assertIn("guard denied", result["error"])
        self.assertEqual(
            target.read_text(encoding="utf-8"),
            original,
        )

        # Guard denial occurs before execution-budget consumption/tool control.
        self.assertEqual(broker.call_count, 0)

    def test_real_write_file_guard_blocks_kernel_before_execution(self):
        self._assert_real_write_denied_before_execution(
            "section_1_central_mind/protected.py"
        )

    def test_real_write_file_guard_blocks_constitution_before_execution(self):
        self._assert_real_write_denied_before_execution(
            "section_2_constitution/protected.txt"
        )

    def test_real_write_file_guard_blocks_memory_before_execution(self):
        self._assert_real_write_denied_before_execution(
            "section_3_memory/entries/protected.json"
        )

    def test_denied_tool_never_executes(self):
        folder = self._make_counting_tool(
            requirement="process.execute",
        )

        guard = self._guard({
            "user": {"workspace.read"},
        })

        broker = ToolBroker(
            self.root,
            self.tools,
            guard=guard,
            principal=self._principal("user"),
            inventory=self._inventory_for(folder),
        )

        result = broker.bind_central_mind().call(
            "counting_tool",
            {},
        )

        self.assertFalse(result["ok"])
        self.assertIn("guard denied", result["error"])

        tool_module = __import__(
            self.package_name + ".engine",
            fromlist=["EXECUTIONS"],
        )

        self.assertEqual(
            tool_module.EXECUTIONS,
            0,
        )

        # Denied calls do not consume execution budget.
        self.assertEqual(
            broker.call_count,
            0,
        )

    def test_passed_tool_executes_exactly_once(self):
        folder = self._make_counting_tool(
            requirement="workspace.read",
        )

        guard = self._guard({
            "user": {"workspace.read"},
        })

        broker = ToolBroker(
            self.root,
            self.tools,
            guard=guard,
            principal=self._principal("user"),
            inventory=self._inventory_for(folder),
        )

        result = broker.bind_central_mind().call(
            "counting_tool",
            {},
        )

        self.assertTrue(result["ok"])
        self.assertEqual(
            result["data"]["executions"],
            1,
        )
        self.assertEqual(
            broker.call_count,
            1,
        )

    def test_missing_security_requirement_fails_closed_in_guarded_mode(self):
        folder = self.tools / "legacy"
        folder.mkdir()

        (folder / "__init__.py").write_text(
            "",
            encoding="utf-8",
        )

        (folder / "engine.py").write_text(
            textwrap.dedent(
                """
                from section_1_central_mind.guard.contract import ToolEffect

                EXECUTIONS = 0

                class LegacyTool:
                    name = "legacy_tool"
                    description = "legacy"
                    parameters = {}

                    def __init__(self, workspace_root, broker):
                        self.workspace_root = workspace_root
                        self.broker = broker

                    def effects(self, args):
                        return (
                            ToolEffect(
                                action="read",
                                target=str(
                                    self.workspace_root
                                    / "legacy-test-input.txt"
                                ),
                                scope="exact",
                            ),
                        )

                    def call(self, args):
                        global EXECUTIONS
                        EXECUTIONS += 1
                        return {
                            "ok": True,
                            "data": None,
                            "error": None,
                        }

                TOOLS = [LegacyTool]
                """
            ),
            encoding="utf-8",
        )

        (folder / "__manifest__.py").write_text(
            textwrap.dedent(
                """
                ORGAN = {
                    "name": "legacy",
                    "kind": "tool",
                    "scope": "outside_guards",
                    "capabilities": ["legacy_tool"],
                    "entry_module": "legacy.engine",
                    "entry_attr": "TOOLS",
                }
                """
            ),
            encoding="utf-8",
        )

        guard = self._guard({
            "administrator": {
                "workspace.read",
                "workspace.write",
                "process.execute",
            },
        })

        broker = ToolBroker(
            self.root,
            self.tools,
            guard=guard,
            principal=self._principal("administrator"),
            inventory=self._inventory_for(folder),
        )

        result = broker.bind_central_mind().call(
            "legacy_tool",
            {},
        )

        self.assertFalse(result["ok"])
        self.assertIn(
            "no required security capability",
            result["error"],
        )

        tool_module = __import__(
            "legacy.engine",
            fromlist=["EXECUTIONS"],
        )

        self.assertEqual(
            tool_module.EXECUTIONS,
            0,
        )

    def test_model_args_cannot_reduce_manifest_requirement(self):
        folder = self._make_counting_tool(
            requirement="process.execute",
        )

        guard = self._guard({
            "user": {"workspace.read"},
        })

        broker = ToolBroker(
            self.root,
            self.tools,
            guard=guard,
            principal=self._principal("user"),
            inventory=self._inventory_for(folder),
        )

        result = broker.bind_central_mind().call(
            "counting_tool",
            {
                "required_capabilities": [
                    "workspace.read"
                ],
                "security": {
                    "requires": [
                        "workspace.read"
                    ]
                },
            },
        )

        self.assertFalse(result["ok"])

        tool_module = __import__(
            self.package_name + ".engine",
            fromlist=["EXECUTIONS"],
        )

        self.assertEqual(
            tool_module.EXECUTIONS,
            0,
        )

    def test_guardless_bound_execution_fails_closed_before_tool_control(self):
        folder = self._make_counting_tool()

        broker = ToolBroker(
            self.root,
            self.tools,
        )

        result = broker.bind_central_mind().call(
            "counting_tool",
            {},
        )

        self.assertFalse(result["ok"])
        self.assertIn(
            "trusted execution context is not installed",
            result["error"],
        )
        self.assertEqual(broker.call_count, 0)

        counter = folder / "count.txt"
        self.assertFalse(counter.exists())

    def test_guard_without_principal_is_configuration_error(self):
        self._make_counting_tool()

        guard = self._guard({
            "user": {"workspace.read"},
        })

        with self.assertRaises(ValueError):
            ToolBroker(
                self.root,
                self.tools,
                guard=guard,
                principal=None,
            )

    def test_principal_without_guard_is_configuration_error(self):
        self._make_counting_tool()

        with self.assertRaises(ValueError):
            ToolBroker(
                self.root,
                self.tools,
                guard=None,
                principal=self._principal("user"),
            )


if __name__ == "__main__":
    unittest.main()
