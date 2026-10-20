"""Generic capability policy for the Guard Layer.

A component may DECLARE capabilities that an action requires.

Declarations never grant authority.

Only trusted Guard policy determines which capabilities a principal
has been granted. The policy engine knows capabilities, not individual
tool/domain/model names.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, Iterable, Mapping, Tuple

from .contract import GuardPrincipal


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    required: FrozenSet[str]
    granted: FrozenSet[str]
    missing: FrozenSet[str]
    reason: str


class GuardPolicy:
    """Evaluate required capabilities against trusted grants."""

    def __init__(
        self,
        *,
        human_role_grants: Mapping[str, Iterable[str]] | None = None,
        internal_grants: Mapping[str, Iterable[str]] | None = None,
    ):
        self._human_role_grants = self._normalize_grants(
            human_role_grants or {}
        )
        self._internal_grants = self._normalize_grants(
            internal_grants or {}
        )

    @staticmethod
    def _normalize_capability(value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("capability must be a string")

        value = value.strip().lower()

        if not value:
            raise ValueError("capability must not be empty")

        parts = value.split(".")

        if any(
            not part
            or not all(
                ch.isalnum() or ch in {"_", "-"}
                for ch in part
            )
            for part in parts
        ):
            raise ValueError(
                f"invalid capability: {value}"
            )

        return value

    @classmethod
    def _normalize_set(
        cls,
        values: Iterable[str],
    ) -> FrozenSet[str]:
        return frozenset(
            cls._normalize_capability(value)
            for value in values
        )

    @classmethod
    def _normalize_grants(
        cls,
        grants: Mapping[str, Iterable[str]],
    ) -> Dict[str, FrozenSet[str]]:
        normalized: Dict[str, FrozenSet[str]] = {}

        for key, values in grants.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("grant identity must be a non-empty string")

            normalized[key.strip().lower()] = cls._normalize_set(values)

        return normalized

    def grants_for(
        self,
        principal: GuardPrincipal,
    ) -> FrozenSet[str]:
        if not isinstance(principal, GuardPrincipal):
            return frozenset()

        if principal.kind == "human":
            if principal.authenticated is not True:
                return frozenset()

            role = principal.role.strip().lower()

            if not role:
                return frozenset()

            return self._human_role_grants.get(
                role,
                frozenset(),
            )

        if principal.kind == "internal":
            return self._internal_grants.get(
                principal.principal_id.strip().lower(),
                frozenset(),
            )

        return frozenset()

    def evaluate(
        self,
        principal: GuardPrincipal,
        required: Iterable[str],
    ) -> PolicyDecision:
        try:
            required_set = self._normalize_set(required)
        except (TypeError, ValueError) as exc:
            return PolicyDecision(
                allowed=False,
                required=frozenset(),
                granted=frozenset(),
                missing=frozenset(),
                reason=f"invalid capability requirement: {exc}",
            )

        # An action with no declared requirement is NOT implicitly safe.
        # It has not declared enough information for authorization.
        if not required_set:
            return PolicyDecision(
                allowed=False,
                required=required_set,
                granted=frozenset(),
                missing=frozenset(),
                reason="action declares no required security capability",
            )

        granted = self.grants_for(principal)
        missing = required_set - granted

        if missing:
            return PolicyDecision(
                allowed=False,
                required=required_set,
                granted=granted,
                missing=missing,
                reason=(
                    "principal lacks required capabilities: "
                    + ", ".join(sorted(missing))
                ),
            )

        return PolicyDecision(
            allowed=True,
            required=required_set,
            granted=granted,
            missing=frozenset(),
            reason="all required capabilities are explicitly granted",
        )
