"""Generic model-resource selection for AI Friend.

This module owns no cognitive authority.

Central Mind supplies a resource requirement. Registered models are scored
from declared metadata, bootstrap hints and learned evidence. Model names are
selection results, never architectural assumptions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class ResourceRequirement:
    capability: str = ""
    domain: Optional[str] = None
    traits: Tuple[str, ...] = ()
    avoid_traits: Tuple[str, ...] = ()
    structured_output: Optional[str] = None
    minimum_quality: float = 0.0
    context_tokens: int = 0
    prefer_local: bool = True
    latency_preference: Optional[str] = None

    @classmethod
    def from_mapping(
        cls,
        value: Optional[Mapping[str, Any]],
    ) -> "ResourceRequirement":
        value = value or {}

        def strings(item):
            if isinstance(item, str):
                item = [item]
            if not isinstance(item, (list, tuple)):
                return ()
            return tuple(
                str(x).strip().lower()
                for x in item
                if str(x).strip()
            )

        try:
            quality = float(
                value.get("minimum_quality", 0.0)
                or 0.0
            )
        except (TypeError, ValueError):
            quality = 0.0

        try:
            context = int(
                value.get("context_tokens", 0)
                or 0
            )
        except (TypeError, ValueError):
            context = 0

        return cls(
            capability=str(
                value.get("capability") or ""
            ).strip().lower(),
            domain=(
                str(value.get("domain")).strip().lower()
                if value.get("domain")
                else None
            ),
            traits=strings(
                value.get("traits")
            ),
            avoid_traits=strings(
                value.get("avoid_traits")
            ),
            structured_output=(
                str(
                    value.get("structured_output")
                ).strip().lower()
                if value.get("structured_output")
                else None
            ),
            minimum_quality=max(
                0.0,
                min(1.0, quality),
            ),
            context_tokens=max(
                0,
                context,
            ),
            prefer_local=bool(
                value.get("prefer_local", True)
            ),
            latency_preference=(
                str(
                    value.get("latency_preference")
                ).strip().lower()
                if value.get("latency_preference")
                else None
            ),
        )


@dataclass(frozen=True)
class ResourceCandidate:
    key: str
    score: float
    reasons: Tuple[str, ...] = ()
    resource: Dict[str, Any] = field(
        default_factory=dict
    )


def _strings(value) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple, set)):
        return []
    return [
        str(item).strip().lower()
        for item in value
        if str(item).strip()
    ]


def _blob(resource: Mapping[str, Any]) -> str:
    values = []

    for key in (
        "kind",
        "role",
        "description",
        "reasoning_leak",
        "provider",
    ):
        value = resource.get(key)
        if value is not None:
            values.append(str(value))

    for key in (
        "best_tasks",
        "strengths",
        "weaknesses",
        "avoid",
        "capabilities",
        "tasks",
        "specialties",
    ):
        values.extend(
            _strings(resource.get(key))
        )

    return " ".join(values).lower()


def _installed(resource: Mapping[str, Any]) -> bool:
    if resource.get("installed") is False:
        return False

    status = str(
        resource.get("status") or ""
    ).lower()

    return not any(
        token in status
        for token in (
            "incomplete",
            "missing",
            "unavailable",
            "not_installed",
        )
    )


def _quality(
    resource: Mapping[str, Any],
    requirement: ResourceRequirement,
) -> float:
    capability = requirement.capability

    candidates = [
        resource.get("quality_score"),
        resource.get("quality"),
    ]

    task_quality = resource.get(
        "task_quality"
    )

    if isinstance(task_quality, Mapping):
        candidates.insert(
            0,
            task_quality.get(capability),
        )

    best = 0.0

    for value in candidates:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue

        if number > 1.0:
            number /= 100.0

        best = max(
            best,
            max(0.0, min(1.0, number)),
        )

    return best


def _eligible(
    resource: Mapping[str, Any],
    requirement: ResourceRequirement,
) -> Tuple[bool, List[str]]:
    reasons = []

    if not _installed(resource):
        return False, ["not installed"]

    domain = requirement.domain

    excluded = set(
        _strings(
            resource.get("excluded_domains")
        )
    )

    if domain and domain in excluded:
        return False, [
            f"excluded from domain {domain}"
        ]

    eligible = set(
        _strings(
            resource.get("eligible_domains")
        )
    )

    if (
        domain
        and eligible
        and domain not in eligible
    ):
        return False, [
            f"not eligible for domain {domain}"
        ]

    required_context = (
        requirement.context_tokens
    )

    if required_context:
        declared = (
            resource.get("context_tokens")
            or resource.get("context_window")
            or 0
        )

        try:
            declared = int(declared)
        except (TypeError, ValueError):
            declared = 0

        if declared < required_context:
            return False, [
                "context window below requirement"
            ]

    return True, reasons


def rank_resources(
    resources: Mapping[str, Mapping[str, Any]],
    requirement: ResourceRequirement | Mapping[str, Any],
    *,
    bootstrap_priority: Sequence[str] = (),
    learned_scores: Optional[Mapping[str, Any]] = None,
) -> List[ResourceCandidate]:
    """Rank available resources without granting authority."""

    if not isinstance(
        requirement,
        ResourceRequirement,
    ):
        requirement = (
            ResourceRequirement.from_mapping(
                requirement
            )
        )

    learned_scores = learned_scores or {}

    priority_index = {
        str(key): index
        for index, key in enumerate(
            bootstrap_priority
        )
    }

    ranked = []

    for key, resource in resources.items():
        if not isinstance(resource, Mapping):
            continue

        allowed, rejection = _eligible(
            resource,
            requirement,
        )

        if not allowed:
            continue

        score = 0.0
        reasons = []
        blob = _blob(resource)

        quality = _quality(
            resource,
            requirement,
        )

        if quality:
            score += quality * 100.0
            reasons.append(
                f"declared quality {quality:.2f}"
            )

        if (
            requirement.minimum_quality
            and quality
            < requirement.minimum_quality
        ):
            continue

        quality_part = score

        for trait in requirement.traits:
            if trait in blob:
                score += 8.0
                reasons.append(
                    f"matches trait {trait}"
                )

        for trait in requirement.avoid_traits:
            if trait in blob:
                score -= 10.0
                reasons.append(
                    f"avoid trait {trait}"
                )

        if requirement.capability:
            if requirement.capability in blob:
                score += 10.0
                reasons.append(
                    "matches requested capability"
                )

        if requirement.structured_output:
            structured = set(
                _strings(
                    resource.get(
                        "structured_output"
                    )
                )
            )

            if (
                requirement.structured_output
                in structured
                or requirement.structured_output
                in blob
            ):
                score += 8.0
                reasons.append(
                    "structured-output fit"
                )

        if requirement.prefer_local:
            provider = str(
                resource.get("provider")
                or resource.get("runtime")
                or ""
            ).lower()

            if provider not in {
                "openai",
                "openai_compat",
                "http",
            }:
                score += 2.0
                reasons.append(
                    "local-resource preference"
                )

        # Declared capability quality dominates the ranking. Trait and keyword
        # matches only break ties, so they cannot outweigh a clearly stronger model.
        bonus = score - quality_part
        score = quality_part + max(-10.0, min(10.0, bonus))

        learned = learned_scores.get(key)

        if isinstance(learned, Mapping):
            learned = (
                learned.get("score")
                or learned.get("quality_score")
                or 0.0
            )

        try:
            learned = float(learned or 0.0)
        except (TypeError, ValueError):
            learned = 0.0

        if learned:
            score += learned * 10.0
            reasons.append(
                f"learned evidence {learned:.3f}"
            )

        if key in priority_index:
            # Bootstrap is intentionally a weak tie-breaking hint.
            boost = max(
                0.0,
                3.0
                - priority_index[key] * 0.1,
            )
            score += boost
            reasons.append(
                "trainer bootstrap hint"
            )

        ranked.append(
            ResourceCandidate(
                key=str(key),
                score=score,
                reasons=tuple(reasons),
                resource=dict(resource),
            )
        )

    ranked.sort(
        key=lambda item: (
            -item.score,
            item.key,
        )
    )

    return ranked
