from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from section_1_central_mind.guard.resources import ResourceClassifier


class FakeInventory:
    def __init__(self, items):
        self._items = list(items)

    def all(self):
        return list(self._items)


class GuardResourceClassifierTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()

        coder = self.root / "section_5_domains" / "coding"
        filesystem = self.root / "section_8_tools" / "filesystem"

        coder.mkdir(parents=True)
        filesystem.mkdir(parents=True)

        self.inventory = FakeInventory([
            SimpleNamespace(
                name="coder",
                kind="domain",
                path=coder,
            ),
            SimpleNamespace(
                name="filesystem",
                kind="tool",
                path=filesystem,
            ),
        ])

        self.classifier = ResourceClassifier(
            self.root,
            self.inventory,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_kernel_is_classified_before_generic_workspace(self):
        target = (
            self.root
            / "section_1_central_mind"
            / "guard"
            / "policy.py"
        )

        result = self.classifier.classify(target)

        self.assertEqual(result.kind, "kernel")

    def test_constitution_is_classified(self):
        result = self.classifier.classify(
            "section_2_constitution/core.md"
        )

        self.assertEqual(result.kind, "constitution")

    def test_memory_is_classified(self):
        result = self.classifier.classify(
            "section_3_memory/entries/example.json"
        )

        self.assertEqual(result.kind, "memory")

    def test_runtime_state_is_classified(self):
        result = self.classifier.classify(
            ".central_mind/proposals/pending.json"
        )

        self.assertEqual(result.kind, "runtime_state")

    def test_registered_domain_has_trusted_owner(self):
        result = self.classifier.classify(
            "section_5_domains/coding/writer.py"
        )

        self.assertEqual(result.kind, "component")
        self.assertEqual(result.owner_name, "coder")
        self.assertEqual(result.owner_kind, "domain")
        self.assertEqual(
            result.owner_root,
            "section_5_domains/coding",
        )

    def test_registered_tool_has_trusted_owner(self):
        result = self.classifier.classify(
            "section_8_tools/filesystem/filesystem.py"
        )

        self.assertEqual(result.kind, "component")
        self.assertEqual(result.owner_name, "filesystem")
        self.assertEqual(result.owner_kind, "tool")

    def test_workspace_is_classified(self):
        result = self.classifier.classify(
            "section_10_workspace/project/example.py"
        )

        self.assertEqual(result.kind, "workspace")

    def test_data_is_classified(self):
        result = self.classifier.classify(
            "section_9_data/example.json"
        )

        self.assertEqual(result.kind, "data")

    def test_top_level_project_file_is_workspace(self):
        result = self.classifier.classify("Readme.md")

        self.assertEqual(result.kind, "workspace")

    def test_external_path_is_explicitly_external(self):
        outside = self.root.parent / "outside.txt"

        result = self.classifier.classify(outside)

        self.assertEqual(result.kind, "external")
        self.assertEqual(result.relative_path, "")

    def test_parent_escape_becomes_external(self):
        result = self.classifier.classify("../escape.txt")

        self.assertEqual(result.kind, "external")

    def test_inventory_owner_outside_project_fails_closed(self):
        outside_inventory = FakeInventory([
            SimpleNamespace(
                name="bad",
                kind="tool",
                path=self.root.parent / "outside_component",
            )
        ])

        with self.assertRaises(ValueError):
            ResourceClassifier(
                self.root,
                outside_inventory,
            )


if __name__ == "__main__":
    unittest.main()
