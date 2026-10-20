"""Production configuration for Guard authorization.

Capability authority and effect/resource authority remain separate gates.

Capabilities are intentionally open-ended. This module grants only the
capabilities currently authorized for trusted production human roles.
A newly introduced capability is denied automatically until explicitly
granted here.

Process execution is intentionally ungranted until constrained execution
has its own security contract.
"""
from __future__ import annotations

from .effect_policy import EffectPolicy
from .policy import GuardPolicy


def build_production_guard_policy() -> GuardPolicy:
    """Return explicit fail-closed production capability grants.

    The vocabulary is not closed: GuardPolicy accepts future capability
    names generically. Capabilities not explicitly granted here remain
    denied by default.
    """

    return GuardPolicy(
        human_role_grants={
            "administrator": {
                "workspace.read",
                "network.access",
            },
            "trainer": {
                "workspace.read",
                "workspace.write",
                "knowledge.propose",
                "network.access",
                # Narrow Coding V1 test authority. This does NOT grant
                # general process execution.
                "code.test.execute",
            },
            "user": {
                "workspace.read",
                "network.access",
            },
        },
        # Internal components do not acquire human authority merely because
        # they execute inside Central Mind. Authenticated server operations
        # retain the initiating human principal instead.
        internal_grants={},
    )


def build_production_effect_policy() -> EffectPolicy:
    """Return the explicit fail-closed production effect policy."""

    return EffectPolicy(
        resource_rules={
            # Ordinary project/workspace material.
            "workspace": {
                "read": {"exact", "children", "tree"},
                "write": {"exact", "tree"},
                "create": {"exact"},
            },

            # Registered components are additionally constrained by
            # EffectPolicy's effective-requester ownership rules.
            "component": {
                "read": {"exact", "children", "tree"},
            },

            # Central Mind may inspect protected architecture, but ordinary
            # tool effects may never mutate Kernel or Constitution.
            "kernel": {
                "read": {"exact", "children", "tree"},
            },
            "constitution": {
                "read": {"exact", "children", "tree"},
            },

            # This exact rule is ONLY boundary-root visibility. Direct
            # filesystem access to Memory remains hard-blocked by
            # EffectPolicy regardless of this configuration.
            "memory": {
                "read": {"exact"},
            },

            # Runtime state is ordinary operational state, not Memory.
            "runtime_state": {
                "read": {"exact", "children", "tree"},
                "write": {"exact", "tree"},
                "create": {"exact"},
            },

            # Data may be inspected. Mutation is intentionally not granted
            # until a concrete data-writing workflow requires it.
            "data": {
                "read": {"exact", "children", "tree"},
            },
        },
        semantic_rules={
            # Local model/service invocation.
            "service": {"service"},

            # Public network operations. GuardPolicy still separately
            # requires the operation's declared network capability.
            "network": {"service"},

            # Memory Service proposals/operations. Direct Memory filesystem
            # access remains prohibited.
            "memory": {"service"},

            # Process effects are structurally permitted here only after
            # the separate capability gate passes. General run_command still
            # requires process.execute, which production grants to nobody.
            "execute": {"service"},
        },
    )
