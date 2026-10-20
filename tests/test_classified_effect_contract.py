from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from section_1_central_mind.guard.contract import (
    ClassifiedEffect,
    ResourceBoundary,
)
from section_1_central_mind.guard.resources import ResourceDescriptor


class ClassifiedEffectContractTests(unittest.TestCase):

    def resource(self):
        return ResourceDescriptor(
            kind="workspace",
            path=Path("/tmp/project/file.txt"),
            relative_path="file.txt",
        )

    def test_filesystem_effect_requires_resource(self):
        effect = ClassifiedEffect(
            action="READ",
            scope="EXACT",
            resource=self.resource(),
        )

        self.assertEqual(effect.action, "read")
        self.assertEqual(effect.scope, "exact")
        self.assertEqual(effect.target, "")
        self.assertIsNotNone(effect.resource)

    def test_semantic_effect_requires_target(self):
        effect = ClassifiedEffect(
            action="SERVICE",
            scope="SERVICE",
            target=" model:chat ",
        )

        self.assertEqual(effect.action, "service")
        self.assertEqual(effect.scope, "service")
        self.assertEqual(effect.target, "model:chat")
        self.assertIsNone(effect.resource)

    def test_both_resource_and_target_are_rejected(self):
        with self.assertRaises(ValueError):
            ClassifiedEffect(
                action="read",
                scope="exact",
                resource=self.resource(),
                target="something",
            )

    def test_neither_resource_nor_target_is_rejected(self):
        with self.assertRaises(ValueError):
            ClassifiedEffect(
                action="read",
                scope="exact",
            )

    def test_filesystem_action_cannot_use_semantic_target(self):
        with self.assertRaises(ValueError):
            ClassifiedEffect(
                action="write",
                scope="exact",
                target="workspace:file.txt",
            )

    def test_semantic_action_cannot_use_filesystem_resource(self):
        with self.assertRaises(ValueError):
            ClassifiedEffect(
                action="network",
                scope="service",
                resource=self.resource(),
            )

    def test_unknown_action_is_rejected(self):
        with self.assertRaises(ValueError):
            ClassifiedEffect(
                action="teleport",
                scope="service",
                target="somewhere",
            )

    def test_filesystem_effect_accepts_children_scope(self):
        effect = ClassifiedEffect(
            action="read",
            scope=" CHILDREN ",
            resource=self.resource(),
        )

        self.assertEqual(effect.scope, "children")
        self.assertIsNotNone(effect.resource)
        self.assertEqual(effect.target, "")

    def test_boundaries_default_to_empty_tuple(self):
        effect = ClassifiedEffect(
            action="read",
            scope="tree",
            resource=self.resource(),
        )

        self.assertEqual(effect.boundaries, ())
        self.assertIsInstance(effect.boundaries, tuple)

    def test_filesystem_tree_accepts_resource_boundaries(self):
        boundary = ResourceDescriptor(
            kind="kernel",
            path=Path("/tmp/project/section_1_central_mind"),
            relative_path="section_1_central_mind",
        )

        effect = ClassifiedEffect(
            action="read",
            scope="tree",
            resource=self.resource(),
            boundaries=(ResourceBoundary(resource=boundary, scope="tree"),),
        )

        self.assertEqual(effect.boundaries[0].resource, boundary)

    def test_boundary_preserves_exact_reach(self):
        boundary = ResourceBoundary(
            resource=ResourceDescriptor(
                kind="kernel",
                path=Path("/tmp/project/section_1_central_mind"),
                relative_path="section_1_central_mind",
            ),
            scope="exact",
        )

        self.assertEqual(boundary.scope, "exact")

    def test_boundary_preserves_tree_reach(self):
        boundary = ResourceBoundary(
            resource=ResourceDescriptor(
                kind="kernel",
                path=Path("/tmp/project/section_1_central_mind"),
                relative_path="section_1_central_mind",
            ),
            scope="tree",
        )

        self.assertEqual(boundary.scope, "tree")

    def test_boundary_rejects_children_scope(self):
        with self.assertRaises(ValueError):
            ResourceBoundary(
                resource=ResourceDescriptor(
                    kind="kernel",
                    path=Path("/tmp/project/section_1_central_mind"),
                    relative_path="section_1_central_mind",
                ),
                scope="children",
            )

    def test_boundaries_must_be_tuple(self):
        boundary = ResourceDescriptor(
            kind="kernel",
            path=Path("/tmp/project/section_1_central_mind"),
            relative_path="section_1_central_mind",
        )

        with self.assertRaises(ValueError):
            ClassifiedEffect(
                action="read",
                scope="tree",
                resource=self.resource(),
                boundaries=[boundary],
            )

    def test_boundary_members_must_be_resource_descriptors(self):
        with self.assertRaises(ValueError):
            ClassifiedEffect(
                action="read",
                scope="tree",
                resource=self.resource(),
                boundaries=("forged",),
            )

    def test_semantic_effect_cannot_carry_filesystem_boundaries(self):
        boundary = ResourceDescriptor(
            kind="workspace",
            path=Path("/tmp/project/workspace"),
            relative_path="workspace",
        )

        with self.assertRaises(ValueError):
            ClassifiedEffect(
                action="service",
                scope="service",
                target="model:chat",
                boundaries=(ResourceBoundary(resource=boundary, scope="tree"),),
            )

    def test_exact_filesystem_effect_cannot_carry_descendant_boundaries(self):
        boundary = ResourceDescriptor(
            kind="kernel",
            path=Path("/tmp/project/section_1_central_mind"),
            relative_path="section_1_central_mind",
        )

        with self.assertRaises(ValueError):
            ClassifiedEffect(
                action="read",
                scope="exact",
                resource=self.resource(),
                boundaries=(ResourceBoundary(resource=boundary, scope="tree"),),
            )


    def test_unknown_scope_is_rejected(self):
        with self.assertRaises(ValueError):
            ClassifiedEffect(
                action="service",
                scope="universe",
                target="model:chat",
            )

    def test_is_immutable(self):
        effect = ClassifiedEffect(
            action="service",
            scope="service",
            target="model:chat",
        )

        with self.assertRaises(FrozenInstanceError):
            effect.target = "forged"

    def test_serializes_filesystem_effect(self):
        effect = ClassifiedEffect(
            action="read",
            scope="tree",
            resource=self.resource(),
        )

        data = effect.to_dict()

        self.assertEqual(data["action"], "read")
        self.assertEqual(data["scope"], "tree")
        self.assertEqual(
            data["resource"]["kind"],
            "workspace",
        )
        self.assertEqual(data["target"], "")
        self.assertEqual(data["boundaries"], [])

    def test_serializes_semantic_effect(self):
        effect = ClassifiedEffect(
            action="network",
            scope="service",
            target="https://example.com",
        )

        data = effect.to_dict()

        self.assertEqual(data, {
            "action": "network",
            "scope": "service",
            "resource": None,
            "target": "https://example.com",
            "boundaries": [],
        })


if __name__ == "__main__":
    unittest.main(verbosity=2)
