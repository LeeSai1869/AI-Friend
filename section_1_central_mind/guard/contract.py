"""Universal request contract for the Central Mind Guard Layer.

Every protected action enters the Guard Layer through the same envelope.

The envelope describes a request. It does NOT grant authority.

Human authority must originate from trusted authentication/session state.
Component identity must originate from trusted runtime registration.
Client/model supplied strings are descriptive data only unless a trusted
boundary has explicitly converted them into trusted identity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import time
import uuid
from typing import Any, Dict, Mapping

from .resources import ResourceDescriptor


VALID_PRINCIPAL_KINDS = {
    "human",
    "internal",
}

VALID_COMPONENT_KINDS = {
    "central_mind",
    "domain",
    "tool",
    "capability",
    "model",
    "service",
    "guard",
    "chatbox",
}


VALID_EFFECT_ACTIONS = frozenset({
    "read",
    "write",
    "create",
    "execute",
    "service",
    "network",
    "memory",
})


# Effect scope semantics:
#
# exact
#     Only the named filesystem resource.
#
# children
#     The named directory and its immediate children only.
#
# tree
#     The named directory/resource and all descendants recursively.
#
# service
#     The named semantic target for execute/service/network/memory effects.
#
# Scope describes reach. It grants no authority by itself.
VALID_EFFECT_SCOPES = frozenset({
    "exact",
    "children",
    "tree",
    "service",
})


@dataclass(frozen=True)
class ToolEffect:
    """One immutable intended side effect of a tool call.

    This object describes WHAT the tool intends to do before execution.
    It does not classify the target and it grants no authority.

    Resource classification and authorization happen later at trusted
    Guard boundaries.
    """

    action: str
    target: str
    scope: str = "exact"

    def __post_init__(self) -> None:
        if not isinstance(self.action, str):
            raise ValueError("effect action must be a string")

        action = self.action.strip().lower()

        if action not in VALID_EFFECT_ACTIONS:
            raise ValueError(
                f"unsupported effect action: {self.action!r}"
            )

        if not isinstance(self.target, str):
            raise ValueError("effect target must be a string")

        target = self.target.strip()

        if not target:
            raise ValueError("effect target is required")

        if not isinstance(self.scope, str):
            raise ValueError("effect scope must be a string")

        scope = self.scope.strip().lower()

        if scope not in VALID_EFFECT_SCOPES:
            raise ValueError(
                f"unsupported effect scope: {self.scope!r}"
            )

        object.__setattr__(self, "action", action)
        object.__setattr__(self, "target", target)
        object.__setattr__(self, "scope", scope)

    def to_dict(self) -> Dict[str, str]:
        return {
            "action": self.action,
            "target": self.target,
            "scope": self.scope,
        }


@dataclass(frozen=True)
class ResourceBoundary:
    """One semantic filesystem boundary crossed by a scoped effect.

    The trusted classifier records both the semantic resource and the
    actual reach with which the parent operation crosses that resource.

    exact
        The boundary root itself is reached, but its descendants are not.

    tree
        The operation recursively enters the semantic resource.

    A boundary grants no authority. It only preserves classification facts
    for later authorization.
    """

    resource: ResourceDescriptor
    scope: str

    def __post_init__(self) -> None:
        if not isinstance(self.resource, ResourceDescriptor):
            raise ValueError(
                "boundary resource must be a ResourceDescriptor"
            )

        if not isinstance(self.scope, str):
            raise ValueError("boundary scope must be a string")

        scope = self.scope.strip().lower()

        if scope not in {"exact", "tree"}:
            raise ValueError(
                f"unsupported boundary scope: {self.scope!r}"
            )

        object.__setattr__(self, "scope", scope)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource": self.resource.to_dict(),
            "scope": self.scope,
        }


@dataclass(frozen=True)
class ClassifiedEffect:
    """One ToolEffect after trusted resource classification.

    Filesystem effects carry a ResourceDescriptor produced by the trusted
    ResourceClassifier.

    Semantic effects carry a semantic target such as a model service,
    executable, memory service, or network destination.

    Exactly one target representation is allowed.
    """

    action: str
    scope: str
    resource: ResourceDescriptor | None = None
    target: str = ""
    boundaries: tuple[ResourceBoundary, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.action, str):
            raise ValueError("classified effect action must be a string")

        action = self.action.strip().lower()

        if action not in VALID_EFFECT_ACTIONS:
            raise ValueError(
                f"unsupported classified effect action: {self.action!r}"
            )

        if not isinstance(self.scope, str):
            raise ValueError("classified effect scope must be a string")

        scope = self.scope.strip().lower()

        if scope not in VALID_EFFECT_SCOPES:
            raise ValueError(
                f"unsupported classified effect scope: {self.scope!r}"
            )

        if self.resource is not None and not isinstance(
            self.resource,
            ResourceDescriptor,
        ):
            raise ValueError(
                "resource must be ResourceDescriptor or None"
            )

        if not isinstance(self.target, str):
            raise ValueError("classified effect target must be a string")

        if not isinstance(self.boundaries, tuple):
            raise ValueError(
                "classified effect boundaries must be a tuple"
            )

        for boundary in self.boundaries:
            if not isinstance(boundary, ResourceBoundary):
                raise ValueError(
                    "classified effect boundaries must contain "
                    "ResourceBoundary members"
                )

        target = self.target.strip()

        has_resource = self.resource is not None
        has_target = bool(target)

        if has_resource == has_target:
            raise ValueError(
                "classified effect requires exactly one of "
                "resource or semantic target"
            )

        filesystem_actions = {
            "read",
            "write",
            "create",
        }

        semantic_actions = {
            "execute",
            "service",
            "network",
            "memory",
        }

        if action in filesystem_actions and not has_resource:
            raise ValueError(
                f"{action} effect requires a classified filesystem resource"
            )

        if action in semantic_actions and not has_target:
            raise ValueError(
                f"{action} effect requires a semantic target"
            )

        if action in semantic_actions and self.boundaries:
            raise ValueError(
                "semantic effects cannot carry filesystem boundaries"
            )

        if (
            action in filesystem_actions
            and scope == "exact"
            and self.boundaries
        ):
            raise ValueError(
                "exact filesystem effects cannot carry "
                "descendant boundaries"
            )

        object.__setattr__(self, "action", action)
        object.__setattr__(self, "scope", scope)
        object.__setattr__(self, "target", target)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "scope": self.scope,
            "resource": (
                self.resource.to_dict()
                if self.resource is not None
                else None
            ),
            "target": self.target,
            "boundaries": [
                boundary.to_dict()
                for boundary in self.boundaries
            ],
        }


@dataclass(frozen=True)
class GuardPrincipal:
    """Trusted identity presented to the Guard Layer."""

    principal_id: str
    kind: str
    role: str = ""
    authenticated: bool = False
    source: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.principal_id, str) or not self.principal_id.strip():
            raise ValueError("principal_id is required")

        if self.kind not in VALID_PRINCIPAL_KINDS:
            raise ValueError(f"invalid principal kind: {self.kind}")

        if not isinstance(self.role, str):
            raise ValueError("role must be a string")

        if not isinstance(self.authenticated, bool):
            raise ValueError("authenticated must be boolean")

        if not isinstance(self.source, str):
            raise ValueError("source must be a string")


@dataclass(frozen=True)
class GuardComponent:
    """Registered runtime component requesting an action."""

    kind: str
    name: str

    def __post_init__(self) -> None:
        if self.kind not in VALID_COMPONENT_KINDS:
            raise ValueError(f"invalid component kind: {self.kind}")

        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("component name is required")


@dataclass(frozen=True)
class GuardRequest:
    """One universal auditable action request."""

    principal: GuardPrincipal
    component: GuardComponent
    operation: str
    resource: str
    target: str = ""
    scope: str = ""
    required_capabilities: tuple[str, ...] = ()
    component_chain: tuple[GuardComponent, ...] = ()
    effects: tuple[ClassifiedEffect, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    action_id: str = field(
        default_factory=lambda: f"act_{uuid.uuid4().hex}"
    )
    created_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not isinstance(self.principal, GuardPrincipal):
            raise ValueError("principal must be GuardPrincipal")

        if not isinstance(self.component, GuardComponent):
            raise ValueError("component must be GuardComponent")

        if not isinstance(self.operation, str) or not self.operation.strip():
            raise ValueError("operation is required")

        if not isinstance(self.resource, str) or not self.resource.strip():
            raise ValueError("resource is required")

        if not isinstance(self.target, str):
            raise ValueError("target must be a string")

        if not isinstance(self.scope, str):
            raise ValueError("scope must be a string")

        if not isinstance(self.required_capabilities, tuple):
            raise ValueError(
                "required_capabilities must be a tuple"
            )

        if not isinstance(self.component_chain, tuple):
            raise ValueError(
                "component_chain must be a tuple"
            )

        if not isinstance(self.effects, tuple):
            raise ValueError(
                "effects must be a tuple"
            )

        for effect in self.effects:
            if not isinstance(effect, ClassifiedEffect):
                raise ValueError(
                    "effects members must be ClassifiedEffect"
                )

        for member in self.component_chain:
            if not isinstance(member, GuardComponent):
                raise ValueError(
                    "component_chain members must be GuardComponent"
                )

        if (
            self.component_chain
            and self.component_chain[-1] != self.component
        ):
            raise ValueError(
                "component_chain must end with the current component"
            )

        normalized_capabilities = []

        for capability in self.required_capabilities:
            if not isinstance(capability, str):
                raise ValueError(
                    "required capability must be a string"
                )

            capability = capability.strip().lower()

            if not capability:
                raise ValueError(
                    "required capability must not be empty"
                )

            normalized_capabilities.append(capability)

        object.__setattr__(
            self,
            "required_capabilities",
            tuple(normalized_capabilities),
        )

        if not isinstance(self.metadata, Mapping):
            raise ValueError("metadata must be a mapping")

        if not isinstance(self.action_id, str) or not self.action_id.strip():
            raise ValueError("action_id is required")

        if not isinstance(self.created_at, (int, float)):
            raise ValueError("created_at must be numeric")

        # Freeze a shallow copy so later caller mutation cannot silently
        # alter the request metadata held by the Guard Layer.
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_audit_dict(self) -> Dict[str, Any]:
        """Return a plain serializable representation for audit/history."""
        return {
            "action_id": self.action_id,
            "created_at": self.created_at,
            "principal": {
                "principal_id": self.principal.principal_id,
                "kind": self.principal.kind,
                "role": self.principal.role,
                "authenticated": self.principal.authenticated,
                "source": self.principal.source,
            },
            "component": {
                "kind": self.component.kind,
                "name": self.component.name,
            },
            "component_chain": [
                {
                    "kind": member.kind,
                    "name": member.name,
                }
                for member in self.component_chain
            ],
            "operation": self.operation,
            "resource": self.resource,
            "target": self.target,
            "scope": self.scope,
            "required_capabilities": list(
                self.required_capabilities
            ),
            "effects": [
                effect.to_dict()
                for effect in self.effects
            ],
            "metadata": dict(self.metadata),
        }
