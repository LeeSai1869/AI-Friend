from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from section_1_central_mind.guard.resources import (
    ResourceClassifier,
)


class _Info:
    def __init__(self, path, name, kind):
        self.path = path
        self.name = name
        self.kind = kind


class _Inventory:
    def __init__(self, infos):
        self._infos = tuple(infos)

    def all(self):
        return self._infos


class ResourceBoundaryTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()

        paths = [
            "section_1_central_mind",
            "section_2_constitution",
            "section_3_memory",
            "section_5_domains/coding",
            "section_7_models/chat",
            "section_8_tools/filesystem",
            "section_9_data",
            "section_10_workspace",
            ".central_mind",
        ]

        for rel in paths:
            (self.root / rel).mkdir(
                parents=True,
                exist_ok=True,
            )

        inventory = _Inventory([
            _Info(
                self.root / "section_5_domains/coding",
                "coder",
                "domain",
            ),
            _Info(
                self.root / "section_7_models/chat",
                "chat",
                "model",
            ),
            _Info(
                self.root / "section_8_tools/filesystem",
                "filesystem",
                "tool",
            ),
        ])

        self.classifier = ResourceClassifier(
            self.root,
            inventory,
        )

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def identities(boundaries):
        return {
            (
                item.kind,
                item.owner_kind,
                item.owner_name,
                item.relative_path,
            )
            for item in boundaries
        }

    def test_exact_has_no_descendant_boundaries(self):
        resource = self.classifier.classify(self.root)

        self.assertEqual(
            self.classifier.boundaries_within(
                resource,
                "exact",
            ),
            (),
        )

    def test_project_root_tree_finds_protected_and_component_roots(self):
        resource = self.classifier.classify(self.root)

        identities = self.identities(
            self.classifier.boundaries_within(
                resource,
                "tree",
            )
        )

        self.assertIn(
            (
                "kernel",
                "",
                "",
                "section_1_central_mind",
            ),
            identities,
        )
        self.assertIn(
            (
                "constitution",
                "",
                "",
                "section_2_constitution",
            ),
            identities,
        )
        self.assertIn(
            (
                "memory",
                "",
                "",
                "section_3_memory",
            ),
            identities,
        )
        self.assertIn(
            (
                "runtime_state",
                "",
                "",
                ".central_mind",
            ),
            identities,
        )
        self.assertIn(
            (
                "data",
                "",
                "",
                "section_9_data",
            ),
            identities,
        )
        self.assertIn(
            (
                "component",
                "domain",
                "coder",
                "section_5_domains/coding",
            ),
            identities,
        )
        self.assertIn(
            (
                "component",
                "model",
                "chat",
                "section_7_models/chat",
            ),
            identities,
        )
        self.assertIn(
            (
                "component",
                "tool",
                "filesystem",
                "section_8_tools/filesystem",
            ),
            identities,
        )

    def test_project_root_tree_does_not_report_workspace_root_as_crossing(self):
        # The project root itself currently classifies as workspace.
        # section_10_workspace also classifies as workspace, so it is not a
        # different semantic identity and therefore is not a boundary.
        resource = self.classifier.classify(self.root)

        paths = {
            item.relative_path
            for item in self.classifier.boundaries_within(
                resource,
                "tree",
            )
        }

        self.assertNotIn(
            "section_10_workspace",
            paths,
        )

    def test_project_root_children_only_reports_immediate_boundaries(self):
        resource = self.classifier.classify(self.root)

        boundaries = self.classifier.boundaries_within(
            resource,
            "children",
        )

        identities = self.identities(boundaries)

        self.assertIn(
            (
                "kernel",
                "",
                "",
                "section_1_central_mind",
            ),
            identities,
        )
        self.assertIn(
            (
                "constitution",
                "",
                "",
                "section_2_constitution",
            ),
            identities,
        )
        self.assertIn(
            (
                "memory",
                "",
                "",
                "section_3_memory",
            ),
            identities,
        )
        self.assertIn(
            (
                "data",
                "",
                "",
                "section_9_data",
            ),
            identities,
        )
        self.assertIn(
            (
                "runtime_state",
                "",
                "",
                ".central_mind",
            ),
            identities,
        )

        self.assertFalse(
            any(
                item.kind == "component"
                for item in boundaries
            )
        )

    def test_workspace_tree_has_no_crossed_semantic_boundary(self):
        resource = self.classifier.classify(
            self.root / "section_10_workspace"
        )

        self.assertEqual(
            self.classifier.boundaries_within(
                resource,
                "tree",
            ),
            (),
        )

    def test_component_tree_does_not_cross_its_own_identity(self):
        resource = self.classifier.classify(
            self.root / "section_5_domains/coding"
        )

        self.assertEqual(
            self.classifier.boundaries_within(
                resource,
                "tree",
            ),
            (),
        )

    def test_parent_workspace_tree_detects_nested_component(self):
        resource = self.classifier.classify(
            self.root / "section_5_domains"
        )

        boundaries = self.classifier.boundaries_within(
            resource,
            "tree",
        )

        self.assertEqual(len(boundaries), 1)
        self.assertEqual(
            boundaries[0].kind,
            "component",
        )
        self.assertEqual(
            boundaries[0].owner_kind,
            "domain",
        )
        self.assertEqual(
            boundaries[0].owner_name,
            "coder",
        )

    def test_parent_workspace_children_detects_immediate_component(self):
        resource = self.classifier.classify(
            self.root / "section_5_domains"
        )

        boundaries = self.classifier.boundaries_within(
            resource,
            "children",
        )

        self.assertEqual(len(boundaries), 1)
        self.assertEqual(
            boundaries[0].kind,
            "component",
        )
        self.assertEqual(
            boundaries[0].owner_kind,
            "domain",
        )
        self.assertEqual(
            boundaries[0].owner_name,
            "coder",
        )

    def test_project_root_children_does_not_reach_nested_component(self):
        resource = self.classifier.classify(
            self.root
        )

        boundaries = self.classifier.boundaries_within(
            resource,
            "children",
        )

        self.assertFalse(
            any(
                item.kind == "component"
                for item in boundaries
            )
        )

    def test_external_resource_has_no_trusted_project_boundaries(self):
        external = (
            self.root.parent
            / f"{self.root.name}_outside"
        ).resolve()

        resource = self.classifier.classify(external)

        self.assertEqual(resource.kind, "external")
        self.assertEqual(
            self.classifier.boundaries_within(
                resource,
                "tree",
            ),
            (),
        )

    def test_invalid_scope_fails_closed(self):
        resource = self.classifier.classify(self.root)

        with self.assertRaises(ValueError):
            self.classifier.boundaries_within(
                resource,
                "everywhere",
            )

    def test_invalid_resource_contract_is_rejected(self):
        with self.assertRaises(TypeError):
            self.classifier.boundaries_within(
                self.root,
                "tree",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
