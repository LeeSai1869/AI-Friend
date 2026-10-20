from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from section_1_central_mind.guard.contract import (
    ClassifiedEffect,
    ResourceBoundary,
    GuardComponent,
    GuardPrincipal,
    GuardRequest,
)
from section_1_central_mind.guard.resources import ResourceDescriptor


class GuardRequestEffectsTests(unittest.TestCase):

    def setUp(self):
        self.principal = GuardPrincipal(
            principal_id="user-1",
            kind="human",
            role="user",
            authenticated=True,
            source="test",
        )

        self.component = GuardComponent(
            kind="tool",
            name="filesystem",
        )

        self.resource = ResourceDescriptor(
            kind="workspace",
            path=Path("/tmp/project/file.txt"),
            relative_path="file.txt",
        )

    def request(self, **overrides):
        values = {
            "principal": self.principal,
            "component": self.component,
            "component_chain": (self.component,),
            "operation": "example_operation",
            "resource": "tool",
            "target": "example_operation",
            "scope": "",
            "required_capabilities": ("workspace.read",),
        }
        values.update(overrides)
        return GuardRequest(**values)

    def test_legacy_empty_effects_remain_valid_during_migration(self):
        request = self.request()

        self.assertEqual(request.effects, ())

    def test_request_accepts_multiple_classified_effects(self):
        effects = (
            ClassifiedEffect(
                action="read",
                scope="exact",
                resource=self.resource,
            ),
            ClassifiedEffect(
                action="service",
                scope="service",
                target="model:chat",
            ),
        )

        request = self.request(effects=effects)

        self.assertEqual(request.effects, effects)
        self.assertEqual(len(request.effects), 2)

    def test_effects_must_be_tuple(self):
        with self.assertRaises(ValueError):
            self.request(effects=[])

    def test_effect_members_must_be_classified_effects(self):
        with self.assertRaises(ValueError):
            self.request(effects=("forged",))

    def test_effect_tuple_is_immutable(self):
        request = self.request(
            effects=(
                ClassifiedEffect(
                    action="read",
                    scope="exact",
                    resource=self.resource,
                ),
            )
        )

        with self.assertRaises(FrozenInstanceError):
            request.effects = ()

    def test_audit_serializes_all_effects(self):
        request = self.request(
            effects=(
                ClassifiedEffect(
                    action="read",
                    scope="tree",
                    resource=self.resource,
                ),
                ClassifiedEffect(
                    action="network",
                    scope="service",
                    target="https://example.com",
                ),
            )
        )

        record = request.to_audit_dict()

        self.assertEqual(len(record["effects"]), 2)

        self.assertEqual(
            record["effects"][0]["action"],
            "read",
        )
        self.assertEqual(
            record["effects"][0]["resource"]["kind"],
            "workspace",
        )

        self.assertEqual(
            record["effects"][1]["action"],
            "network",
        )
        self.assertEqual(
            record["effects"][1]["target"],
            "https://example.com",
        )

    def test_audit_serializes_effect_boundaries(self):
        boundary = ResourceDescriptor(
            kind="kernel",
            path=Path("/tmp/project/section_1_central_mind"),
            relative_path="section_1_central_mind",
        )

        effect = ClassifiedEffect(
            action="read",
            scope="tree",
            resource=self.resource,
            boundaries=(ResourceBoundary(resource=boundary, scope="tree"),),
        )

        request = self.request(
            effects=(effect,)
        )

        record = request.to_audit_dict()

        self.assertEqual(
            len(record["effects"][0]["boundaries"]),
            1,
        )
        self.assertEqual(
            record["effects"][0]["boundaries"][0]["resource"]["kind"],
            "kernel",
        )
        self.assertEqual(
            record["effects"][0]["boundaries"][0]["resource"][
                "relative_path"
            ],
            "section_1_central_mind",
        )


    def test_caller_cannot_mutate_effect_collection_after_creation(self):
        original = (
            ClassifiedEffect(
                action="service",
                scope="service",
                target="model:chat",
            ),
        )

        request = self.request(effects=original)

        replacement = original + (
            ClassifiedEffect(
                action="network",
                scope="service",
                target="https://evil.example",
            ),
        )

        self.assertEqual(len(request.effects), 1)
        self.assertEqual(len(replacement), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
