from __future__ import annotations

import sys
import tempfile
import textwrap
import unittest
import uuid
from pathlib import Path

from section_1_central_mind.mind.broker import ToolBroker


class BrokerManifestIsolationTests(unittest.TestCase):

    def _write_package(
        self,
        tools_dir: Path,
        folder_name: str,
        runtime_tool_name: str,
        security_requires: dict,
    ):
        folder = tools_dir / folder_name
        folder.mkdir(parents=True)

        package_name = f"pkg_{folder_name}_{uuid.uuid4().hex}"
        package = tools_dir / package_name
        package.mkdir()
        (package / "__init__.py").write_text("", encoding="utf-8")

        (package / "engine.py").write_text(
            textwrap.dedent(
                f"""
                class Tool:
                    name = {runtime_tool_name!r}
                    description = "test tool"
                    parameters = {{}}

                    def __init__(self, workspace_root, broker):
                        self.workspace_root = workspace_root
                        self.broker = broker

                    def call(self, args):
                        return {{
                            "ok": True,
                            "data": {{"tool": self.name}},
                            "error": None,
                        }}

                TOOLS = [Tool]
                """
            ),
            encoding="utf-8",
        )

        (folder / "__manifest__.py").write_text(
            "ORGAN = " + repr({
                "name": folder_name,
                "kind": "tool",
                "scope": "outside_guards",
                "capabilities": [runtime_tool_name],
                "security": {
                    "requires": security_requires,
                },
                "entry_module": f"{package_name}.engine",
                "entry_attr": "TOOLS",
            }),
            encoding="utf-8",
        )

        return package_name

    def test_later_manifest_cannot_claim_earlier_tool_as_its_export(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tools_dir = root / "tools"
            tools_dir.mkdir()

            package_names = []

            package_names.append(
                self._write_package(
                    tools_dir,
                    "a_first",
                    "alpha_tool",
                    {
                        "alpha_tool": ["workspace.read"],
                    },
                )
            )

            package_names.append(
                self._write_package(
                    tools_dir,
                    "b_second",
                    "beta_tool",
                    {
                        "beta_tool": ["workspace.read"],
                        # This declaration is invalid for b_second.
                        # alpha_tool exists globally, but belongs to a_first.
                        "alpha_tool": ["process.execute"],
                    },
                )
            )

            logs = []

            try:
                broker = ToolBroker(
                    workspace_root=root,
                    tools_dir=tools_dir,
                    logger=logs.append,
                )

                self.assertIn("alpha_tool", broker.tools)
                self.assertIn("beta_tool", broker.tools)

                # Earlier manifest's trusted binding must remain untouched.
                self.assertEqual(
                    broker.security_requirements["alpha_tool"],
                    ("workspace.read",),
                )

                self.assertEqual(
                    broker.security_requirements["beta_tool"],
                    ("workspace.read",),
                )

                self.assertTrue(
                    any(
                        "security requirement refers to unregistered tool: alpha_tool"
                        in line
                        for line in logs
                    ),
                    logs,
                )
            finally:
                for name in package_names:
                    sys.modules.pop(name, None)
                    sys.modules.pop(f"{name}.engine", None)

    def test_manifest_tracks_only_its_own_runtime_exports(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            tools_dir = root / "tools"
            tools_dir.mkdir()

            package_name = self._write_package(
                tools_dir,
                "single",
                "real_tool",
                {
                    "real_tool": ["workspace.read"],
                    "ghost_tool": ["workspace.write"],
                },
            )

            logs = []

            try:
                broker = ToolBroker(
                    workspace_root=root,
                    tools_dir=tools_dir,
                    logger=logs.append,
                )

                self.assertEqual(
                    broker.security_requirements["real_tool"],
                    ("workspace.read",),
                )

                self.assertTrue(
                    any(
                        "security requirement refers to unregistered tool: ghost_tool"
                        in line
                        for line in logs
                    ),
                    logs,
                )
            finally:
                sys.modules.pop(package_name, None)
                sys.modules.pop(f"{package_name}.engine", None)


if __name__ == "__main__":
    unittest.main()
