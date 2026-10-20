"""Trusted normalization of declared tool effects for the universal Guard.

This module joins two existing contracts:

    ToolEffect
        describes what a tool intends to do

    ResourceClassifier
        identifies filesystem targets and trusted component ownership

The result is ClassifiedEffect, which is ready to be attached to a
GuardRequest.

This module makes no authorization decision.
"""

from __future__ import annotations

from typing import Iterable

from .contract import (ClassifiedEffect, ResourceBoundary, ToolEffect)
from .resources import ResourceClassifier


FILESYSTEM_EFFECT_ACTIONS = frozenset({
    "read",
    "write",
    "create",
})

SEMANTIC_EFFECT_ACTIONS = frozenset({
    "execute",
    "service",
    "network",
    "memory",
})


class EffectClassifier:
    """Convert declared ToolEffects into trusted ClassifiedEffects."""

    def __init__(self, resource_classifier: ResourceClassifier):
        if not isinstance(resource_classifier, ResourceClassifier):
            raise ValueError(
                "resource_classifier must be ResourceClassifier"
            )

        self.resource_classifier = resource_classifier

    def classify(
        self,
        effects: Iterable[ToolEffect],
    ) -> tuple[ClassifiedEffect, ...]:
        """Classify one complete declared effect set.

        Fail closed when:
        - the collection is malformed,
        - it is empty,
        - a member is not ToolEffect,
        - an action has no known classification path.

        No authorization occurs here.
        """

        if isinstance(effects, (str, bytes)):
            raise ValueError(
                "effects must be an iterable of ToolEffect"
            )

        try:
            declared = tuple(effects)
        except TypeError as exc:
            raise ValueError(
                "effects must be an iterable of ToolEffect"
            ) from exc

        if not declared:
            raise ValueError(
                "tool operation declared no effects"
            )

        classified = []

        for effect in declared:
            if not isinstance(effect, ToolEffect):
                raise ValueError(
                    "effect members must be ToolEffect"
                )

            if effect.action in FILESYSTEM_EFFECT_ACTIONS:
                resource = self.resource_classifier.classify(
                    effect.target
                )

                boundary_resources = (
                    self.resource_classifier.boundaries_within(
                        resource,
                        effect.scope,
                    )
                )

                if effect.scope == "children":
                    boundary_scope = "exact"
                elif effect.scope == "tree":
                    boundary_scope = "tree"
                else:
                    boundary_scope = None

                boundaries = tuple(
                    ResourceBoundary(
                        resource=boundary,
                        scope=boundary_scope,
                    )
                    for boundary in boundary_resources
                )

                classified.append(
                    ClassifiedEffect(
                        action=effect.action,
                        scope=effect.scope,
                        resource=resource,
                        boundaries=boundaries,
                    )
                )
                continue

            if effect.action in SEMANTIC_EFFECT_ACTIONS:
                classified.append(
                    ClassifiedEffect(
                        action=effect.action,
                        scope=effect.scope,
                        target=effect.target,
                    )
                )
                continue

            # ToolEffect currently prevents this state, but this explicit
            # branch preserves fail-closed behavior if the vocabulary grows
            # without updating this classifier.
            raise ValueError(
                "effect action has no trusted classification path: "
                f"{effect.action}"
            )

        return tuple(classified)
