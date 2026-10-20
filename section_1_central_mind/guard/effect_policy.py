"""Generic effect/resource authorization for the universal Guard.

This module answers a different question from GuardPolicy:

    GuardPolicy
        Does the trusted principal possess the capabilities declared by
        the operation?

    EffectPolicy
        Are the complete declared effects permitted to reach these
        classified resources at these scopes through this trusted
        component chain?

EffectPolicy knows generic actions, resource kinds, scopes, semantic
effect classes, and trusted component ownership.

It does NOT know individual tool/domain/model names and it does not grant
human authority.

The default policy is fail closed. Callers must explicitly configure
generic resource/effect rules before an effect can pass.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Iterable, Mapping

from .contract import (
    ClassifiedEffect,
    GuardComponent,
    VALID_EFFECT_ACTIONS,
    VALID_EFFECT_SCOPES,
)
from .resources import RESOURCE_KINDS


FILESYSTEM_ACTIONS = frozenset({
    "read",
    "write",
    "create",
})

SEMANTIC_ACTIONS = frozenset({
    "execute",
    "service",
    "network",
    "memory",
})


@dataclass(frozen=True)
class EffectDecision:
    """Authorization result for one complete atomic effect set."""

    allowed: bool
    reason: str
    denied_index: int | None = None


class EffectPolicy:
    """Evaluate classified effects using generic, explicit rules.

    resource_rules format:

        {
            "workspace": {
                "read": {"exact", "children", "tree"},
                "write": {"exact"},
                "create": {"exact"},
            },
        }

    semantic_rules format:

        {
            "network": {"service"},
            "service": {"service"},
        }

    Rules describe generic action/scope combinations. They do not grant
    capabilities and they do not identify particular tools.

    Component resources receive an additional ownership/coordination check:
    access is permitted only when either:

      - the owning registered component appears in the trusted execution
        chain, or
      - Central Mind appears in the trusted execution chain.

    This preserves hub-and-spoke coordination without tool-name policy.

    Direct filesystem access to the memory resource kind is always blocked.
    Memory Service operations use the separate semantic "memory" effect.

    External filesystem resources are always blocked.

    Kernel and Constitution mutation is always blocked by this generic
    policy. More privileged administrative workflows must use a separate,
    explicit protected-change mechanism rather than ordinary tool effects.
    """

    def __init__(
        self,
        *,
        resource_rules: Mapping[
            str,
            Mapping[str, Iterable[str]],
        ] | None = None,
        semantic_rules: Mapping[
            str,
            Iterable[str],
        ] | None = None,
    ):
        self._resource_rules = self._normalize_resource_rules(
            resource_rules or {}
        )
        self._semantic_rules = self._normalize_semantic_rules(
            semantic_rules or {}
        )

    @staticmethod
    def _normalize_scopes(
        scopes: Iterable[str],
    ) -> FrozenSet[str]:
        if isinstance(scopes, (str, bytes)):
            raise ValueError("effect scopes must be an iterable of strings")

        normalized = set()

        for scope in scopes:
            if not isinstance(scope, str):
                raise ValueError("effect scope must be a string")

            scope = scope.strip().lower()

            if scope not in VALID_EFFECT_SCOPES:
                raise ValueError(
                    f"unsupported effect scope in policy: {scope!r}"
                )

            normalized.add(scope)

        if not normalized:
            raise ValueError("effect scope rule must not be empty")

        return frozenset(normalized)

    @classmethod
    def _normalize_resource_rules(
        cls,
        rules: Mapping[str, Mapping[str, Iterable[str]]],
    ) -> dict[str, dict[str, FrozenSet[str]]]:
        if not isinstance(rules, Mapping):
            raise ValueError("resource_rules must be a mapping")

        normalized = {}

        for resource_kind, action_rules in rules.items():
            if not isinstance(resource_kind, str):
                raise ValueError("resource kind must be a string")

            resource_kind = resource_kind.strip().lower()

            if resource_kind not in RESOURCE_KINDS:
                raise ValueError(
                    f"unsupported resource kind in policy: "
                    f"{resource_kind!r}"
                )

            if not isinstance(action_rules, Mapping):
                raise ValueError(
                    "resource action rules must be a mapping"
                )

            normalized_actions = {}

            for action, scopes in action_rules.items():
                if not isinstance(action, str):
                    raise ValueError("effect action must be a string")

                action = action.strip().lower()

                if action not in FILESYSTEM_ACTIONS:
                    raise ValueError(
                        "resource rules accept only filesystem actions: "
                        f"{action!r}"
                    )

                normalized_actions[action] = cls._normalize_scopes(scopes)

            normalized[resource_kind] = normalized_actions

        return normalized

    @classmethod
    def _normalize_semantic_rules(
        cls,
        rules: Mapping[str, Iterable[str]],
    ) -> dict[str, FrozenSet[str]]:
        if not isinstance(rules, Mapping):
            raise ValueError("semantic_rules must be a mapping")

        normalized = {}

        for action, scopes in rules.items():
            if not isinstance(action, str):
                raise ValueError("semantic action must be a string")

            action = action.strip().lower()

            if action not in SEMANTIC_ACTIONS:
                raise ValueError(
                    f"unsupported semantic action in policy: {action!r}"
                )

            normalized[action] = cls._normalize_scopes(scopes)

        return normalized

    @staticmethod
    def _effective_requester(
        component_chain: tuple[GuardComponent, ...],
    ) -> GuardComponent | None:
        """Return the trusted requester immediately before the tool.

        Normal guarded tool chains are:

            central_mind -> tool
            central_mind -> domain/model -> tool

        The final member is the executing tool. Presence of Central Mind at
        the root of a delegated chain does not itself grant the delegated
        component cross-component authority.
        """
        if len(component_chain) < 2:
            return None

        return component_chain[-2]

    @classmethod
    def _component_access_allowed(
        cls,
        resource,
        component_chain: tuple[GuardComponent, ...],
    ) -> bool:
        requester = cls._effective_requester(component_chain)

        if requester is None:
            return False

        if requester.kind == "central_mind":
            return True

        return (
            requester.kind == resource.owner_kind
            and requester.name == resource.owner_name
        )

    def _evaluate_filesystem_effect(
        self,
        effect: ClassifiedEffect,
        component_chain: tuple[GuardComponent, ...],
    ) -> tuple[bool, str]:
        resource = effect.resource

        if resource is None:
            return False, "filesystem effect has no classified resource"

        # These are hard generic boundaries, not configurable ordinary
        # workspace permissions.
        if resource.kind == "external":
            return False, "external filesystem access is blocked"

        if resource.kind == "memory":
            return (
                False,
                "direct memory filesystem access is blocked; "
                "use the Memory Service",
            )

        if (
            resource.kind in {"kernel", "constitution"}
            and effect.action in {"write", "create"}
        ):
            return (
                False,
                f"{resource.kind} mutation is blocked for ordinary effects",
            )

        if resource.kind == "component":
            if not self._component_access_allowed(
                resource,
                component_chain,
            ):
                return (
                    False,
                    "component resource is outside the effective "
                    "requester's ownership/central-mind authority",
                )

        action_rules = self._resource_rules.get(resource.kind)

        if not action_rules:
            return (
                False,
                f"no effect policy exists for resource kind "
                f"{resource.kind!r}",
            )

        allowed_scopes = action_rules.get(effect.action)

        if not allowed_scopes:
            return (
                False,
                f"{effect.action} is not allowed for resource kind "
                f"{resource.kind!r}",
            )

        if effect.scope not in allowed_scopes:
            return (
                False,
                f"scope {effect.scope!r} is not allowed for "
                f"{effect.action} on {resource.kind!r}",
            )

        return True, "filesystem effect explicitly permitted"

    def _evaluate_boundary(
        self,
        *,
        action: str,
        boundary,
        component_chain: tuple[GuardComponent, ...],
    ) -> tuple[bool, str]:
        """Authorize one crossed semantic boundary exactly as classified.

        A parent ``children`` read can expose the existence of an immediate
        protected root without entering that root. The classifier represents
        that reach as an ``exact`` boundary.

        Memory is therefore allowed one deliberately narrow distinction:

        - direct filesystem access to Memory remains hard-blocked;
        - recursive/tree crossing into Memory remains hard-blocked;
        - Memory mutation remains hard-blocked;
        - only read+exact crossed-boundary visibility may be explicitly
          permitted by the existing resource rule table.

        This is boundary-root visibility, not direct Memory filesystem access.
        """

        resource = boundary.resource

        if (
            resource.kind == "memory"
            and action == "read"
            and boundary.scope == "exact"
        ):
            action_rules = self._resource_rules.get("memory")

            if not action_rules:
                return (
                    False,
                    "memory boundary-root visibility has no explicit "
                    "effect policy",
                )

            allowed_scopes = action_rules.get("read")

            if not allowed_scopes:
                return (
                    False,
                    "memory boundary-root visibility is not allowed",
                )

            if "exact" not in allowed_scopes:
                return (
                    False,
                    "scope 'exact' is not allowed for memory "
                    "boundary-root visibility",
                )

            return (
                True,
                "memory boundary-root visibility explicitly permitted",
            )

        boundary_effect = ClassifiedEffect(
            action=action,
            scope=boundary.scope,
            resource=resource,
        )

        return self._evaluate_filesystem_effect(
            boundary_effect,
            component_chain,
        )

    def _evaluate_semantic_effect(
        self,
        effect: ClassifiedEffect,
    ) -> tuple[bool, str]:
        allowed_scopes = self._semantic_rules.get(effect.action)

        if not allowed_scopes:
            return (
                False,
                f"no semantic effect policy exists for "
                f"{effect.action!r}",
            )

        if effect.scope not in allowed_scopes:
            return (
                False,
                f"scope {effect.scope!r} is not allowed for "
                f"semantic effect {effect.action!r}",
            )

        return True, "semantic effect explicitly permitted"

    def evaluate(
        self,
        effects: Iterable[ClassifiedEffect],
        *,
        component_chain: tuple[GuardComponent, ...] = (),
    ) -> EffectDecision:
        """Evaluate one complete effect set atomically.

        Every effect must pass. One denied effect blocks the whole operation.
        """

        if not isinstance(component_chain, tuple):
            return EffectDecision(
                allowed=False,
                reason="component_chain must be an immutable tuple",
            )

        if any(
            not isinstance(member, GuardComponent)
            for member in component_chain
        ):
            return EffectDecision(
                allowed=False,
                reason="component_chain contains an invalid member",
            )

        if isinstance(effects, (str, bytes)):
            return EffectDecision(
                allowed=False,
                reason="effects must be classified effects",
            )

        try:
            effect_set = tuple(effects)
        except TypeError:
            return EffectDecision(
                allowed=False,
                reason="effects must be iterable",
            )

        if not effect_set:
            return EffectDecision(
                allowed=False,
                reason="action declares no classified effects",
            )

        for index, effect in enumerate(effect_set):
            if not isinstance(effect, ClassifiedEffect):
                return EffectDecision(
                    allowed=False,
                    reason="effect is not a ClassifiedEffect",
                    denied_index=index,
                )

            if effect.action not in VALID_EFFECT_ACTIONS:
                return EffectDecision(
                    allowed=False,
                    reason="effect action is unsupported",
                    denied_index=index,
                )

            if effect.scope not in VALID_EFFECT_SCOPES:
                return EffectDecision(
                    allowed=False,
                    reason="effect scope is unsupported",
                    denied_index=index,
                )

            if effect.action in FILESYSTEM_ACTIONS:
                allowed, reason = self._evaluate_filesystem_effect(
                    effect,
                    component_chain,
                )

                if allowed:
                    for boundary in effect.boundaries:
                        boundary_allowed, boundary_reason = (
                            self._evaluate_boundary(
                                action=effect.action,
                                boundary=boundary,
                                component_chain=component_chain,
                            )
                        )

                        if not boundary_allowed:
                            allowed = False
                            reason = (
                                "crossed semantic boundary denied: "
                                f"{boundary.resource.kind} "
                                f"{boundary.resource.relative_path!r} "
                                f"with scope {boundary.scope!r}: "
                                f"{boundary_reason}"
                            )
                            break
            elif effect.action in SEMANTIC_ACTIONS:
                allowed, reason = self._evaluate_semantic_effect(effect)
            else:
                allowed = False
                reason = "effect has no authorization path"

            if not allowed:
                return EffectDecision(
                    allowed=False,
                    reason=reason,
                    denied_index=index,
                )

        return EffectDecision(
            allowed=True,
            reason="all declared effects are explicitly permitted",
        )
