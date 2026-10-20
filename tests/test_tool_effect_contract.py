from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from section_1_central_mind.guard.contract import ToolEffect
from section_8_tools._base.tool import Tool


class ToolEffectContractTests(unittest.TestCase):

    def test_effect_is_immutable(self):
        effect = ToolEffect(
            action="read",
            target="section_5_domains/coding/writer.py",
        )

        with self.assertRaises(Exception):
            effect.action = "write"

    def test_effect_normalizes_action_target_and_scope(self):
        effect = ToolEffect(
            action=" READ ",
            target=" section_10_workspace/example.py ",
            scope=" EXACT ",
        )

        self.assertEqual(effect.action, "read")
        self.assertEqual(
            effect.target,
            "section_10_workspace/example.py",
        )
        self.assertEqual(effect.scope, "exact")

    def test_effect_rejects_unknown_action(self):
        with self.assertRaises(ValueError):
            ToolEffect(
                action="destroy_everything",
                target="example.py",
            )

    def test_effect_rejects_empty_target(self):
        with self.assertRaises(ValueError):
            ToolEffect(
                action="read",
                target="   ",
            )

    def test_effect_accepts_and_normalizes_children_scope(self):
        effect = ToolEffect(
            action="read",
            target="workspace",
            scope=" CHILDREN ",
        )

        self.assertEqual(effect.scope, "children")

    def test_effect_rejects_unknown_scope(self):
        with self.assertRaises(ValueError):
            ToolEffect(
                action="read",
                target="example.py",
                scope="universe",
            )

    def test_effect_serializes(self):
        effect = ToolEffect(
            action="network",
            target="https://example.com",
            scope="service",
        )

        self.assertEqual(
            effect.to_dict(),
            {
                "action": "network",
                "target": "https://example.com",
                "scope": "service",
            },
        )

    def test_base_tool_effects_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            tool = Tool(
                Path(temp),
                broker=None,
            )

            with self.assertRaises(NotImplementedError):
                tool.effects({})

    def test_concrete_tool_can_return_multiple_effects(self):
        class MultiEffectTool(Tool):
            name = "multi"

            def effects(self, args):
                return (
                    ToolEffect(
                        action="read",
                        target=args["source"],
                    ),
                    ToolEffect(
                        action="write",
                        target=args["destination"],
                    ),
                    ToolEffect(
                        action="execute",
                        target="ffmpeg",
                        scope="service",
                    ),
                )

            def call(self, args):
                return {
                    "ok": True,
                    "data": None,
                    "error": None,
                }

        with tempfile.TemporaryDirectory() as temp:
            tool = MultiEffectTool(
                Path(temp),
                broker=None,
            )

            effects = tool.effects({
                "source": "input.mp4",
                "destination": ".central_mind/frames",
            })

            self.assertIsInstance(effects, tuple)
            self.assertEqual(len(effects), 3)
            self.assertEqual(
                [item.action for item in effects],
                ["read", "write", "execute"],
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
