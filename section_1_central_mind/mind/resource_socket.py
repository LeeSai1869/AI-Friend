"""Universal Central Mind resource socket.

This module defines the stable Central Mind side of cross-section resource
access.  Central Mind expresses WHAT it needs.  Connected sections decide
HOW that requirement is fulfilled.

The socket has no model names, provider names, domain semantics, tool
semantics, registry format, or Section-7-specific selection knowledge.

A connector is simply a trusted callable accepting a generic requirement
dictionary and returning an object capable of fulfilling it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Optional, Tuple


@dataclass(frozen=True)
class ResourceRequirement:
    capability: str
    kind: Optional[str] = None
    domain: Optional[str] = None
    traits: Tuple[str, ...] = field(default_factory=tuple)
    avoid_traits: Tuple[str, ...] = field(default_factory=tuple)
    structured_output: Optional[str] = None
    minimum_quality: float = 0.0
    context_tokens: Optional[int] = None
    prefer_local: bool = False
    latency_preference: Optional[str] = None
    constraints: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "capability": self.capability,
            "kind": self.kind,
            "domain": self.domain,
            "traits": list(self.traits),
            "avoid_traits": list(self.avoid_traits),
            "structured_output": self.structured_output,
            "minimum_quality": self.minimum_quality,
            "context_tokens": self.context_tokens,
            "prefer_local": self.prefer_local,
            "latency_preference": self.latency_preference,
            "constraints": dict(self.constraints),
        }


class ResourceSocket:
    """Stable generic socket for subordinate resources.

    Connectors are implementation-side plugs.  Section 1 does not inspect
    their registries or know how they rank/select implementations.
    """

    def __init__(self):
        self._connectors: Dict[str, Callable[..., Any]] = {}

    def connect(self, kind: str, connector: Callable[..., Any]) -> None:
        key = str(kind or "").strip()
        if not key:
            raise ValueError("resource connector kind is required")
        if not callable(connector):
            raise TypeError("resource connector must be callable")
        self._connectors[key] = connector

    def connected(self, kind: str) -> bool:
        return str(kind or "").strip() in self._connectors

    def request(
        self,
        requirement: ResourceRequirement,
        **context: Any,
    ) -> Any:
        if not isinstance(requirement, ResourceRequirement):
            raise TypeError("requirement must be ResourceRequirement")

        kind = str(requirement.kind or "").strip()
        if not kind:
            raise ValueError("resource requirement kind is required")

        connector = self._connectors.get(kind)
        if connector is None:
            raise RuntimeError(
                f"no trusted resource connector registered for kind {kind!r}"
            )

        return connector(
            requirement=requirement.as_dict(),
            **context,
        )
