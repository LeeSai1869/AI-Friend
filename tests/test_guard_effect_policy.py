from __future__ import annotations

from pathlib import Path
import unittest

from section_1_central_mind.guard.contract import (
    ClassifiedEffect,
    ResourceBoundary,
    GuardComponent,
)
from section_1_central_mind.guard.effect_policy import EffectPolicy
from section_1_central_mind.guard.resources import ResourceDescriptor


class GuardEffectPolicyTests(unittest.TestCase):

    def setUp(self):
        self.policy = EffectPolicy(
            resource_rules={
                "workspace": {
                    "read": {"exact", "children", "tree"},
                    "write": {"exact", "tree"},
                    "create": {"exact"},
                },
                "component": {
                    "read": {"exact", "children", "tree"},
                },
                "kernel": {
                    "read": {"exact", "children", "tree"},
                },
                "constitution": {
                    "read": {"exact", "children", "tree"},
                },
                "runtime_state": {
                    "read": {"exact", "children", "tree"},
                    "write": {"exact", "tree"},
                    "create": {"exact"},
                },
                "data": {
                    "read": {"exact", "children", "tree"},
                },
            },
            semantic_rules={
                "service": {"service"},
                "network": {"service"},
                "execute": {"service"},
                "memory": {"service"},
            },
        )

        self.mind = GuardComponent(
            kind="central_mind",
            name="central_mind",
        )
        self.filesystem = GuardComponent(
            kind="tool",
            name="filesystem",
        )
        self.coder = GuardComponent(
            kind="domain",
            name="coder",
        )

    @staticmethod
    def resource(
        kind,
        path,
        *,
        owner_kind="",
        owner_name="",
        owner_root="",
    ):
        return ResourceDescriptor(
            kind=kind,
            path=Path(path),
            relative_path=str(path),
            owner_kind=owner_kind,
            owner_name=owner_name,
            owner_root=owner_root,
        )

    def fs_effect(self, action, kind, scope="exact", **owner):
        return ClassifiedEffect(
            action=action,
            scope=scope,
            resource=self.resource(
                kind,
                f"/project/{kind}/target",
                **owner,
            ),
        )

    def test_default_policy_fails_closed(self):
        policy = EffectPolicy()

        decision = policy.evaluate((
            self.fs_effect("read", "workspace"),
        ))

        self.assertFalse(decision.allowed)

    def test_empty_effect_set_fails_closed(self):
        decision = self.policy.evaluate(())

        self.assertFalse(decision.allowed)
        self.assertIn("no classified effects", decision.reason)

    def test_explicit_workspace_read_passes(self):
        decision = self.policy.evaluate((
            self.fs_effect("read", "workspace", "exact"),
        ))

        self.assertTrue(decision.allowed)

    def test_scope_must_be_explicitly_permitted(self):
        policy = EffectPolicy(
            resource_rules={
                "workspace": {
                    "read": {"exact"},
                },
            },
        )

        decision = policy.evaluate((
            self.fs_effect("read", "workspace", "tree"),
        ))

        self.assertFalse(decision.allowed)
        self.assertIn("scope", decision.reason)

    def test_external_filesystem_access_is_always_blocked(self):
        policy = EffectPolicy(
            resource_rules={
                "external": {
                    "read": {"exact", "tree"},
                },
            },
        )

        decision = policy.evaluate((
            self.fs_effect("read", "external"),
        ))

        self.assertFalse(decision.allowed)
        self.assertIn("external", decision.reason)

    def test_direct_memory_filesystem_read_is_always_blocked(self):
        policy = EffectPolicy(
            resource_rules={
                "memory": {
                    "read": {"exact", "tree"},
                },
            },
        )

        decision = policy.evaluate((
            self.fs_effect("read", "memory"),
        ))

        self.assertFalse(decision.allowed)
        self.assertIn("Memory Service", decision.reason)

    def test_direct_memory_filesystem_write_is_always_blocked(self):
        policy = EffectPolicy(
            resource_rules={
                "memory": {
                    "write": {"exact"},
                },
            },
        )

        decision = policy.evaluate((
            self.fs_effect("write", "memory"),
        ))

        self.assertFalse(decision.allowed)

    def test_kernel_write_cannot_be_enabled_by_rule_table(self):
        policy = EffectPolicy(
            resource_rules={
                "kernel": {
                    "write": {"exact"},
                },
            },
        )

        decision = policy.evaluate((
            self.fs_effect("write", "kernel"),
        ))

        self.assertFalse(decision.allowed)

    def test_constitution_create_cannot_be_enabled_by_rule_table(self):
        policy = EffectPolicy(
            resource_rules={
                "constitution": {
                    "create": {"exact"},
                },
            },
        )

        decision = policy.evaluate((
            self.fs_effect("create", "constitution"),
        ))

        self.assertFalse(decision.allowed)

    def test_kernel_read_can_be_explicitly_permitted(self):
        decision = self.policy.evaluate((
            self.fs_effect("read", "kernel"),
        ))

        self.assertTrue(decision.allowed)

    def test_component_owner_in_chain_can_read_own_component(self):
        effect = self.fs_effect(
            "read",
            "component",
            owner_kind="domain",
            owner_name="coder",
            owner_root="section_5_domains/coding",
        )

        decision = self.policy.evaluate(
            (effect,),
            component_chain=(
                self.mind,
                self.coder,
                self.filesystem,
            ),
        )

        self.assertTrue(decision.allowed)

    def test_central_mind_can_coordinate_component_read(self):
        effect = self.fs_effect(
            "read",
            "component",
            owner_kind="domain",
            owner_name="coder",
            owner_root="section_5_domains/coding",
        )

        decision = self.policy.evaluate(
            (effect,),
            component_chain=(self.mind, self.filesystem),
        )

        self.assertTrue(decision.allowed)

    def test_unrelated_component_chain_cannot_read_component(self):
        effect = self.fs_effect(
            "read",
            "component",
            owner_kind="domain",
            owner_name="coder",
            owner_root="section_5_domains/coding",
        )

        decision = self.policy.evaluate(
            (effect,),
            component_chain=(self.filesystem,),
        )

        self.assertFalse(decision.allowed)
        self.assertIn(
            "effective requester",
            decision.reason,
        )

    def test_component_write_is_not_implicitly_granted(self):
        effect = self.fs_effect(
            "write",
            "component",
            owner_kind="domain",
            owner_name="coder",
            owner_root="section_5_domains/coding",
        )

        decision = self.policy.evaluate(
            (effect,),
            component_chain=(self.coder,),
        )

        self.assertFalse(decision.allowed)

    def test_service_effect_can_be_explicitly_permitted(self):
        effect = ClassifiedEffect(
            action="service",
            scope="service",
            target="ollama:qwen3-vl:8b",
        )

        decision = self.policy.evaluate((effect,))

        self.assertTrue(decision.allowed)

    def test_network_effect_can_be_explicitly_permitted(self):
        effect = ClassifiedEffect(
            action="network",
            scope="service",
            target="https://example.com",
        )

        decision = self.policy.evaluate((effect,))

        self.assertTrue(decision.allowed)

    def test_execute_effect_can_be_explicitly_permitted(self):
        effect = ClassifiedEffect(
            action="execute",
            scope="service",
            target="ffmpeg",
        )

        decision = self.policy.evaluate((effect,))

        self.assertTrue(decision.allowed)

    def test_semantic_memory_is_distinct_from_memory_filesystem(self):
        effect = ClassifiedEffect(
            action="memory",
            scope="service",
            target="memory-service",
        )

        decision = self.policy.evaluate((effect,))

        self.assertTrue(decision.allowed)

    def test_unknown_semantic_permission_fails_closed(self):
        policy = EffectPolicy()

        effect = ClassifiedEffect(
            action="network",
            scope="service",
            target="https://example.com",
        )

        decision = policy.evaluate((effect,))

        self.assertFalse(decision.allowed)

    def test_one_denied_effect_blocks_entire_effect_set(self):
        effects = (
            self.fs_effect("read", "workspace"),
            self.fs_effect("read", "external"),
        )

        decision = self.policy.evaluate(effects)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.denied_index, 1)

    def test_policy_does_not_depend_on_tool_names(self):
        effect = self.fs_effect("read", "workspace")

        chain_a = (
            self.mind,
            GuardComponent(kind="tool", name="tool_1"),
        )
        chain_b = (
            self.mind,
            GuardComponent(kind="tool", name="future_tool_1000"),
        )

        first = self.policy.evaluate(
            (effect,),
            component_chain=chain_a,
        )
        second = self.policy.evaluate(
            (effect,),
            component_chain=chain_b,
        )

        self.assertEqual(first.allowed, second.allowed)
        self.assertTrue(first.allowed)

    def test_resource_rule_rejects_semantic_action(self):
        with self.assertRaises(ValueError):
            EffectPolicy(
                resource_rules={
                    "workspace": {
                        "network": {"service"},
                    },
                },
            )

    def test_semantic_rule_rejects_filesystem_action(self):
        with self.assertRaises(ValueError):
            EffectPolicy(
                semantic_rules={
                    "read": {"exact"},
                },
            )

    def test_invalid_scope_configuration_is_rejected(self):
        with self.assertRaises(ValueError):
            EffectPolicy(
                resource_rules={
                    "workspace": {
                        "read": {"everywhere"},
                    },
                },
            )


    def test_delegated_domain_does_not_gain_cross_component_access_from_mind_prefix(self):
        effect = self.fs_effect(
            "read",
            "component",
            owner_kind="domain",
            owner_name="other_domain",
            owner_root="section_5_domains/other",
        )

        decision = self.policy.evaluate(
            (effect,),
            component_chain=(
                self.mind,
                self.coder,
                self.filesystem,
            ),
        )

        self.assertFalse(decision.allowed)
        self.assertIn("effective requester", decision.reason)

    def test_delegated_domain_can_read_own_component_through_tool(self):
        effect = self.fs_effect(
            "read",
            "component",
            owner_kind="domain",
            owner_name="coder",
            owner_root="section_5_domains/coding",
        )

        decision = self.policy.evaluate(
            (effect,),
            component_chain=(
                self.mind,
                self.coder,
                self.filesystem,
            ),
        )

        self.assertTrue(decision.allowed)

    def test_direct_central_mind_can_coordinate_component_read_through_tool(self):
        effect = self.fs_effect(
            "read",
            "component",
            owner_kind="domain",
            owner_name="coder",
            owner_root="section_5_domains/coding",
        )

        decision = self.policy.evaluate(
            (effect,),
            component_chain=(
                self.mind,
                self.filesystem,
            ),
        )

        self.assertTrue(decision.allowed)

    def test_workspace_tree_crossing_memory_is_blocked_atomically(self):
        memory = self.resource(
            "memory",
            "/project/section_3_memory",
        )

        effect = ClassifiedEffect(
            action="read",
            scope="tree",
            resource=self.resource(
                "workspace",
                "/project",
            ),
            boundaries=(ResourceBoundary(resource=memory, scope="tree"),),
        )

        decision = self.policy.evaluate((effect,))

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.denied_index, 0)
        self.assertIn(
            "crossed semantic boundary denied",
            decision.reason,
        )
        self.assertIn("Memory Service", decision.reason)

    def test_workspace_tree_crossing_kernel_requires_kernel_read_rule(self):
        policy = EffectPolicy(
            resource_rules={
                "workspace": {
                    "read": {"tree"},
                },
            },
        )

        kernel = self.resource(
            "kernel",
            "/project/section_1_central_mind",
        )

        effect = ClassifiedEffect(
            action="read",
            scope="tree",
            resource=self.resource(
                "workspace",
                "/project",
            ),
            boundaries=(ResourceBoundary(resource=kernel, scope="tree"),),
        )

        decision = policy.evaluate((effect,))

        self.assertFalse(decision.allowed)
        self.assertIn("kernel", decision.reason)

    def test_workspace_tree_crossing_explicit_kernel_read_can_pass(self):
        kernel = self.resource(
            "kernel",
            "/project/section_1_central_mind",
        )

        effect = ClassifiedEffect(
            action="read",
            scope="tree",
            resource=self.resource(
                "workspace",
                "/project",
            ),
            boundaries=(ResourceBoundary(resource=kernel, scope="tree"),),
        )

        decision = self.policy.evaluate((effect,))

        self.assertTrue(decision.allowed)

    def test_crossed_component_obeys_effective_requester_rule(self):
        other = self.resource(
            "component",
            "/project/section_5_domains/other",
            owner_kind="domain",
            owner_name="other_domain",
            owner_root="section_5_domains/other",
        )

        effect = ClassifiedEffect(
            action="read",
            scope="tree",
            resource=self.resource(
                "workspace",
                "/project/section_5_domains",
            ),
            boundaries=(ResourceBoundary(resource=other, scope="tree"),),
        )

        decision = self.policy.evaluate(
            (effect,),
            component_chain=(
                self.mind,
                self.coder,
                self.filesystem,
            ),
        )

        self.assertFalse(decision.allowed)
        self.assertIn(
            "crossed semantic boundary denied",
            decision.reason,
        )

    def test_crossed_own_component_can_pass_for_effective_requester(self):
        own = self.resource(
            "component",
            "/project/section_5_domains/coding",
            owner_kind="domain",
            owner_name="coder",
            owner_root="section_5_domains/coding",
        )

        effect = ClassifiedEffect(
            action="read",
            scope="tree",
            resource=self.resource(
                "workspace",
                "/project/section_5_domains",
            ),
            boundaries=(ResourceBoundary(resource=own, scope="tree"),),
        )

        decision = self.policy.evaluate(
            (effect,),
            component_chain=(
                self.mind,
                self.coder,
                self.filesystem,
            ),
        )

        self.assertTrue(decision.allowed)

    def test_children_crossing_uses_exact_boundary_scope(self):
        policy = EffectPolicy(
            resource_rules={
                "workspace": {
                    "read": {"children"},
                },
                "kernel": {
                    "read": {"exact"},
                },
            },
        )

        kernel = self.resource(
            "kernel",
            "/project/section_1_central_mind",
        )

        effect = ClassifiedEffect(
            action="read",
            scope="children",
            resource=self.resource(
                "workspace",
                "/project",
            ),
            boundaries=(
                ResourceBoundary(
                    resource=kernel,
                    scope="exact",
                ),
            ),
        )

        decision = policy.evaluate((effect,))

        self.assertTrue(decision.allowed)

    def test_memory_exact_boundary_visibility_requires_explicit_rule(self):
        memory = self.resource(
            "memory",
            "/project/section_3_memory",
        )

        effect = ClassifiedEffect(
            action="read",
            scope="children",
            resource=self.resource(
                "workspace",
                "/project",
            ),
            boundaries=(
                ResourceBoundary(
                    resource=memory,
                    scope="exact",
                ),
            ),
        )

        without_memory_rule = EffectPolicy(
            resource_rules={
                "workspace": {
                    "read": {"children"},
                },
            },
        )

        denied = without_memory_rule.evaluate((effect,))

        self.assertFalse(denied.allowed)

        with_memory_root_visibility = EffectPolicy(
            resource_rules={
                "workspace": {
                    "read": {"children"},
                },
                "memory": {
                    "read": {"exact"},
                },
            },
        )

        allowed = with_memory_root_visibility.evaluate((effect,))

        self.assertTrue(allowed.allowed)

    def test_memory_tree_boundary_remains_blocked_even_if_configured(self):
        memory = self.resource(
            "memory",
            "/project/section_3_memory",
        )

        effect = ClassifiedEffect(
            action="read",
            scope="tree",
            resource=self.resource(
                "workspace",
                "/project",
            ),
            boundaries=(
                ResourceBoundary(
                    resource=memory,
                    scope="tree",
                ),
            ),
        )

        policy = EffectPolicy(
            resource_rules={
                "workspace": {
                    "read": {"tree"},
                },
                "memory": {
                    "read": {"tree"},
                },
            },
        )

        decision = policy.evaluate((effect,))

        self.assertFalse(decision.allowed)
        self.assertIn("Memory Service", decision.reason)

    def test_memory_exact_boundary_write_remains_blocked(self):
        memory = self.resource(
            "memory",
            "/project/section_3_memory",
        )

        effect = ClassifiedEffect(
            action="write",
            scope="tree",
            resource=self.resource(
                "workspace",
                "/project",
            ),
            boundaries=(
                ResourceBoundary(
                    resource=memory,
                    scope="exact",
                ),
            ),
        )

        policy = EffectPolicy(
            resource_rules={
                "workspace": {
                    "write": {"tree"},
                },
                "memory": {
                    "write": {"exact"},
                },
            },
        )

        decision = policy.evaluate((effect,))

        self.assertFalse(decision.allowed)
        self.assertIn("Memory Service", decision.reason)

    def test_direct_memory_exact_read_stays_blocked_when_boundary_visibility_is_configured(self):
        policy = EffectPolicy(
            resource_rules={
                "memory": {
                    "read": {"exact"},
                },
            },
        )

        direct = ClassifiedEffect(
            action="read",
            scope="exact",
            resource=self.resource(
                "memory",
                "/project/section_3_memory",
            ),
        )

        decision = policy.evaluate((direct,))

        self.assertFalse(decision.allowed)
        self.assertIn("Memory Service", decision.reason)

    def test_tree_crossing_requires_tree_boundary_authority(self):
        policy = EffectPolicy(
            resource_rules={
                "workspace": {
                    "read": {"tree"},
                },
                "kernel": {
                    "read": {"exact"},
                },
            },
        )

        kernel = self.resource(
            "kernel",
            "/project/section_1_central_mind",
        )

        effect = ClassifiedEffect(
            action="read",
            scope="tree",
            resource=self.resource(
                "workspace",
                "/project",
            ),
            boundaries=(
                ResourceBoundary(
                    resource=kernel,
                    scope="tree",
                ),
            ),
        )

        decision = policy.evaluate((effect,))

        self.assertFalse(decision.allowed)
        self.assertIn("scope", decision.reason)

    def test_one_denied_boundary_blocks_whole_multi_effect_operation(self):
        safe = self.fs_effect(
            "read",
            "workspace",
            "exact",
        )

        memory = self.resource(
            "memory",
            "/project/section_3_memory",
        )

        broad = ClassifiedEffect(
            action="read",
            scope="tree",
            resource=self.resource(
                "workspace",
                "/project",
            ),
            boundaries=(ResourceBoundary(resource=memory, scope="tree"),),
        )

        decision = self.policy.evaluate(
            (safe, broad),
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.denied_index, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
