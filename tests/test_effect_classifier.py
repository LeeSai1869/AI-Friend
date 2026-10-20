from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from section_1_central_mind.guard.contract import (
    ClassifiedEffect,
    ToolEffect,
)
from section_1_central_mind.guard.effects import EffectClassifier
from section_1_central_mind.guard.resources import ResourceClassifier


class FakeInfo:
    def __init__(self, name, kind, path):
        self.name = name
        self.kind = kind
        self.path = path


class FakeInventory:
    def __init__(self, infos=()):
        self._infos = tuple(infos)

    def all(self):
        return self._infos


class EffectClassifierTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()

        (self.root / "section_1_central_mind").mkdir()
        (self.root / "section_2_constitution").mkdir()
        (self.root / "section_3_memory").mkdir()
        (self.root / "section_9_data").mkdir()
        (self.root / "section_10_workspace").mkdir()
        (self.root / ".central_mind").mkdir()

        tool_root = (
            self.root
            / "section_8_tools"
            / "filesystem"
        )
        tool_root.mkdir(parents=True)

        inventory = FakeInventory((
            FakeInfo(
                "filesystem",
                "tool",
                tool_root,
            ),
        ))

        self.resources = ResourceClassifier(
            self.root,
            inventory,
        )

        self.classifier = EffectClassifier(
            self.resources
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_filesystem_effect_is_resource_classified(self):
        target = (
            self.root
            / "section_10_workspace"
            / "notes.txt"
        )

        result = self.classifier.classify((
            ToolEffect(
                action="read",
                target=str(target),
                scope="exact",
            ),
        ))

        self.assertEqual(len(result), 1)
        self.assertIsInstance(
            result[0],
            ClassifiedEffect,
        )
        self.assertEqual(result[0].action, "read")
        self.assertEqual(
            result[0].resource.kind,
            "workspace",
        )
        self.assertEqual(result[0].target, "")

    def test_exact_filesystem_effect_has_no_boundaries(self):
        target = (
            self.root
            / "section_10_workspace"
            / "notes.txt"
        )

        result = self.classifier.classify((
            ToolEffect(
                action="read",
                target=str(target),
                scope="exact",
            ),
        ))

        self.assertEqual(result[0].boundaries, ())

    def test_project_root_tree_carries_crossed_semantic_boundaries(self):
        result = self.classifier.classify((
            ToolEffect(
                action="read",
                target=str(self.root),
                scope="tree",
            ),
        ))

        effect = result[0]

        kinds = {
            boundary.resource.kind
            for boundary in effect.boundaries
        }

        self.assertIn("kernel", kinds)
        self.assertIn("constitution", kinds)
        self.assertIn("memory", kinds)
        self.assertIn("runtime_state", kinds)
        self.assertIn("data", kinds)
        self.assertIn("component", kinds)

    def test_workspace_tree_without_nested_semantic_roots_has_no_boundaries(self):
        result = self.classifier.classify((
            ToolEffect(
                action="read",
                target=str(
                    self.root / "section_10_workspace"
                ),
                scope="tree",
            ),
        ))

        self.assertEqual(result[0].boundaries, ())

    def test_parent_children_carries_immediate_component_boundary(self):
        parent = self.root / "section_8_tools"

        result = self.classifier.classify((
            ToolEffect(
                action="read",
                target=str(parent),
                scope="children",
            ),
        ))

        boundaries = result[0].boundaries

        self.assertEqual(len(boundaries), 1)
        self.assertEqual(
            boundaries[0].resource.kind,
            "component",
        )
        self.assertEqual(
            boundaries[0].resource.owner_name,
            "filesystem",
        )

    def test_children_boundary_records_exact_reach(self):
        parent = self.root / "section_8_tools"

        result = self.classifier.classify((
            ToolEffect(
                action="read",
                target=str(parent),
                scope="children",
            ),
        ))

        self.assertEqual(
            result[0].boundaries[0].scope,
            "exact",
        )

    def test_tree_boundaries_record_tree_reach(self):
        result = self.classifier.classify((
            ToolEffect(
                action="read",
                target=str(self.root),
                scope="tree",
            ),
        ))

        self.assertTrue(result[0].boundaries)

        self.assertTrue(all(
            boundary.scope == "tree"
            for boundary in result[0].boundaries
        ))

    def test_semantic_effect_has_no_boundaries(self):
        result = self.classifier.classify((
            ToolEffect(
                action="service",
                target="model:chat",
                scope="service",
            ),
        ))

        self.assertEqual(result[0].boundaries, ())


    def test_registered_component_ownership_is_preserved(self):
        target = (
            self.root
            / "section_8_tools"
            / "filesystem"
            / "filesystem.py"
        )

        result = self.classifier.classify((
            ToolEffect(
                action="read",
                target=str(target),
                scope="exact",
            ),
        ))

        resource = result[0].resource

        self.assertEqual(resource.kind, "component")
        self.assertEqual(
            resource.owner_name,
            "filesystem",
        )
        self.assertEqual(
            resource.owner_kind,
            "tool",
        )

    def test_protected_kernel_target_is_preserved(self):
        target = (
            self.root
            / "section_1_central_mind"
            / "mind"
            / "loop.py"
        )

        result = self.classifier.classify((
            ToolEffect(
                action="write",
                target=str(target),
                scope="exact",
            ),
        ))

        self.assertEqual(
            result[0].resource.kind,
            "kernel",
        )

    def test_external_filesystem_target_remains_external(self):
        outside = (
            self.root.parent
            / "outside-ai-friend-test.txt"
        )

        result = self.classifier.classify((
            ToolEffect(
                action="read",
                target=str(outside),
                scope="exact",
            ),
        ))

        self.assertEqual(
            result[0].resource.kind,
            "external",
        )

    def test_service_effect_remains_semantic(self):
        result = self.classifier.classify((
            ToolEffect(
                action="service",
                target="model:chat",
                scope="service",
            ),
        ))

        self.assertEqual(
            result[0].target,
            "model:chat",
        )
        self.assertIsNone(result[0].resource)

    def test_network_effect_remains_semantic(self):
        result = self.classifier.classify((
            ToolEffect(
                action="network",
                target="https://example.com",
                scope="service",
            ),
        ))

        self.assertEqual(
            result[0].target,
            "https://example.com",
        )
        self.assertIsNone(result[0].resource)

    def test_memory_effect_remains_semantic(self):
        result = self.classifier.classify((
            ToolEffect(
                action="memory",
                target="memory:knowledge_proposal",
                scope="service",
            ),
        ))

        self.assertEqual(
            result[0].target,
            "memory:knowledge_proposal",
        )

    def test_execute_effect_remains_semantic(self):
        result = self.classifier.classify((
            ToolEffect(
                action="execute",
                target="ffmpeg",
                scope="service",
            ),
        ))

        self.assertEqual(result[0].target, "ffmpeg")

    def test_multiple_effects_preserve_order(self):
        target = (
            self.root
            / "section_10_workspace"
            / "input.txt"
        )

        result = self.classifier.classify((
            ToolEffect(
                action="read",
                target=str(target),
                scope="exact",
            ),
            ToolEffect(
                action="service",
                target="model:chat",
                scope="service",
            ),
            ToolEffect(
                action="network",
                target="https://example.com",
                scope="service",
            ),
        ))

        self.assertEqual(
            [effect.action for effect in result],
            ["read", "service", "network"],
        )

    def test_empty_effect_set_fails_closed(self):
        with self.assertRaises(ValueError):
            self.classifier.classify(())

    def test_non_effect_member_fails_closed(self):
        with self.assertRaises(ValueError):
            self.classifier.classify((
                "forged",
            ))

    def test_string_collection_fails_closed(self):
        with self.assertRaises(ValueError):
            self.classifier.classify(
                "not-effects"
            )

    def test_result_is_immutable_tuple(self):
        target = (
            self.root
            / "section_10_workspace"
            / "input.txt"
        )

        result = self.classifier.classify((
            ToolEffect(
                action="read",
                target=str(target),
                scope="exact",
            ),
        ))

        self.assertIsInstance(result, tuple)


if __name__ == "__main__":
    unittest.main(verbosity=2)
