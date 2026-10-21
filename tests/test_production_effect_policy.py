from pathlib import Path
import tempfile
import unittest

from section_1_central_mind.guard.contract import (
    ClassifiedEffect,
    GuardComponent,
    ResourceBoundary,
)
from section_1_central_mind.guard.production_policy import (
    build_production_effect_policy,
)
from section_1_central_mind.guard.resources import ResourceDescriptor


class ProductionEffectPolicyTests(unittest.TestCase):

    def setUp(self):
        self.policy = build_production_effect_policy()

    @staticmethod
    def resource(kind, path="/project/item", **kwargs):
        return ResourceDescriptor(
            kind=kind,
            path=path,
            relative_path=kwargs.pop("relative_path", "item"),
            **kwargs,
        )

    @staticmethod
    def chain(*items):
        return tuple(
            GuardComponent(kind=kind, name=name)
            for kind, name in items
        )

    def test_workspace_read_is_enabled(self):
        effect = ClassifiedEffect(
            action="read",
            scope="exact",
            resource=self.resource("workspace"),
        )

        decision = self.policy.evaluate(
            (effect,),
            component_chain=self.chain(
                ("central_mind", "central_mind"),
                ("tool", "filesystem"),
            ),
        )

        self.assertTrue(decision.allowed)

    def test_workspace_exact_create_is_enabled(self):
        effect = ClassifiedEffect(
            action="create",
            scope="exact",
            resource=self.resource("workspace"),
        )

        decision = self.policy.evaluate(
            (effect,),
            component_chain=self.chain(
                ("central_mind", "central_mind"),
                ("tool", "folders"),
            ),
        )

        self.assertTrue(decision.allowed)

    def test_execute_effect_is_structural_not_a_capability_grant(self):
        effect = ClassifiedEffect(
            action="execute",
            scope="service",
            target="ffmpeg",
        )

        decision = self.policy.evaluate(
            (effect,),
            component_chain=self.chain(
                ("central_mind", "central_mind"),
                ("tool", "vision"),
            ),
        )

        self.assertTrue(decision.allowed)
        # The effect gate permits the shape; production capability policy
        # must independently deny general process execution for every role.
        from section_1_central_mind.guard.contract import GuardPrincipal, GuardRequest
        from section_1_central_mind.guard.production_policy import build_production_guard_policy
        for role in ("user", "trainer", "administrator"):
            request = GuardRequest(
                principal=GuardPrincipal(principal_id="test", kind="human", role=role,
                                         authenticated=True, source="auth_service"),
                component=GuardComponent(kind="tool", name="terminal"),
                component_chain=self.chain(("central_mind", "central_mind"), ("tool", "terminal")),
                operation="run_command", resource="tool", target="run_command",
                required_capabilities=("process.execute",), effects=(effect,),
            )
            self.assertFalse(build_production_guard_policy().evaluate(request.principal, request.required_capabilities).allowed)

    def test_network_is_enabled(self):
        effect = ClassifiedEffect(
            action="network",
            scope="service",
            target="https://example.com",
        )

        decision = self.policy.evaluate(
            (effect,),
            component_chain=self.chain(
                ("central_mind", "central_mind"),
                ("tool", "web"),
            ),
        )

        self.assertTrue(decision.allowed)

    def test_service_is_enabled(self):
        effect = ClassifiedEffect(
            action="service",
            scope="service",
            target="model:chat",
        )

        decision = self.policy.evaluate(
            (effect,),
            component_chain=self.chain(
                ("central_mind", "central_mind"),
                ("tool", "intake"),
            ),
        )

        self.assertTrue(decision.allowed)

    def test_memory_service_is_enabled(self):
        effect = ClassifiedEffect(
            action="memory",
            scope="service",
            target="memory:knowledge_proposal",
        )

        decision = self.policy.evaluate(
            (effect,),
            component_chain=self.chain(
                ("central_mind", "central_mind"),
                ("tool", "intake"),
            ),
        )

        self.assertTrue(decision.allowed)

    def test_direct_memory_filesystem_read_remains_blocked(self):
        effect = ClassifiedEffect(
            action="read",
            scope="exact",
            resource=self.resource(
                "memory",
                "/project/section_3_memory",
                relative_path="section_3_memory",
            ),
        )

        decision = self.policy.evaluate(
            (effect,),
            component_chain=self.chain(
                ("central_mind", "central_mind"),
                ("tool", "filesystem"),
            ),
        )

        self.assertFalse(decision.allowed)

    def test_memory_root_visibility_can_be_crossed_exactly(self):
        memory = self.resource(
            "memory",
            "/project/section_3_memory",
            relative_path="section_3_memory",
        )

        effect = ClassifiedEffect(
            action="read",
            scope="children",
            resource=self.resource(
                "workspace",
                "/project",
                relative_path=".",
            ),
            boundaries=(
                ResourceBoundary(
                    resource=memory,
                    scope="exact",
                ),
            ),
        )

        decision = self.policy.evaluate(
            (effect,),
            component_chain=self.chain(
                ("central_mind", "central_mind"),
                ("tool", "filesystem"),
            ),
        )

        self.assertTrue(decision.allowed)

    def test_recursive_memory_boundary_remains_blocked(self):
        memory = self.resource(
            "memory",
            "/project/section_3_memory",
            relative_path="section_3_memory",
        )

        effect = ClassifiedEffect(
            action="read",
            scope="tree",
            resource=self.resource(
                "workspace",
                "/project",
                relative_path=".",
            ),
            boundaries=(
                ResourceBoundary(
                    resource=memory,
                    scope="tree",
                ),
            ),
        )

        decision = self.policy.evaluate(
            (effect,),
            component_chain=self.chain(
                ("central_mind", "central_mind"),
                ("tool", "filesystem"),
            ),
        )

        self.assertFalse(decision.allowed)

    def test_kernel_mutation_remains_blocked(self):
        effect = ClassifiedEffect(
            action="write",
            scope="exact",
            resource=self.resource(
                "kernel",
                "/project/section_1_central_mind/example.py",
                relative_path="section_1_central_mind/example.py",
            ),
        )

        decision = self.policy.evaluate(
            (effect,),
            component_chain=self.chain(
                ("central_mind", "central_mind"),
                ("tool", "filesystem"),
            ),
        )

        self.assertFalse(decision.allowed)

    def test_constitution_mutation_remains_blocked(self):
        effect = ClassifiedEffect(
            action="create",
            scope="exact",
            resource=self.resource(
                "constitution",
                "/project/section_2_constitution/new.md",
                relative_path="section_2_constitution/new.md",
            ),
        )

        decision = self.policy.evaluate(
            (effect,),
            component_chain=self.chain(
                ("central_mind", "central_mind"),
                ("tool", "filesystem"),
            ),
        )

        self.assertFalse(decision.allowed)

    def test_delegated_component_cannot_read_other_component(self):
        target = self.resource(
            "component",
            "/project/section_5_domains/general",
            relative_path="section_5_domains/general",
            owner_name="general",
            owner_kind="domain",
            owner_root="/project/section_5_domains/general",
        )

        effect = ClassifiedEffect(
            action="read",
            scope="tree",
            resource=target,
        )

        decision = self.policy.evaluate(
            (effect,),
            component_chain=self.chain(
                ("central_mind", "central_mind"),
                ("domain", "coder"),
                ("tool", "filesystem"),
            ),
        )

        self.assertFalse(decision.allowed)

    def test_delegated_component_can_read_itself(self):
        target = self.resource(
            "component",
            "/project/section_5_domains/coding",
            relative_path="section_5_domains/coding",
            owner_name="coder",
            owner_kind="domain",
            owner_root="/project/section_5_domains/coding",
        )

        effect = ClassifiedEffect(
            action="read",
            scope="tree",
            resource=target,
        )

        decision = self.policy.evaluate(
            (effect,),
            component_chain=self.chain(
                ("central_mind", "central_mind"),
                ("domain", "coder"),
                ("tool", "filesystem"),
            ),
        )

        self.assertTrue(decision.allowed)

    def test_direct_central_mind_can_coordinate_component_read(self):
        target = self.resource(
            "component",
            "/project/section_5_domains/general",
            relative_path="section_5_domains/general",
            owner_name="general",
            owner_kind="domain",
            owner_root="/project/section_5_domains/general",
        )

        effect = ClassifiedEffect(
            action="read",
            scope="tree",
            resource=target,
        )

        decision = self.policy.evaluate(
            (effect,),
            component_chain=self.chain(
                ("central_mind", "central_mind"),
                ("tool", "filesystem"),
            ),
        )

        self.assertTrue(decision.allowed)


if __name__ == "__main__":
    unittest.main()
