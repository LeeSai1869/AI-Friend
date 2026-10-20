"""Trusted resource classification for the universal Guard.

This module answers only WHAT a target is and, for registered components,
WHO owns that target.

It makes no authorization decision.

Component ownership comes from the already-discovered Inventory. Manifests
do not get a second ownership declaration here.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


RESOURCE_KINDS = frozenset({
    "kernel",
    "constitution",
    "memory",
    "component",
    "workspace",
    "data",
    "runtime_state",
    "external",
})


@dataclass(frozen=True)
class ResourceDescriptor:
    kind: str
    path: Path
    relative_path: str = ""
    owner_name: str = ""
    owner_kind: str = ""
    owner_root: str = ""

    def __post_init__(self) -> None:
        if self.kind not in RESOURCE_KINDS:
            raise ValueError(
                f"Unsupported resource kind: {self.kind!r}"
            )

        if self.kind == "component":
            if not self.owner_name or not self.owner_kind or not self.owner_root:
                raise ValueError(
                    "Component resources require owner_name, "
                    "owner_kind, and owner_root."
                )

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "path": str(self.path),
            "relative_path": self.relative_path,
            "owner_name": self.owner_name,
            "owner_kind": self.owner_kind,
            "owner_root": self.owner_root,
        }


class ResourceClassifier:
    """Classify filesystem targets using trusted project structure."""

    def __init__(
        self,
        project_root: Path,
        inventory,
        *,
        workspace_root: Path | None = None,
    ):
        self.project_root = Path(project_root).resolve()
        self.authorized_workspace_root = (
            Path(workspace_root).resolve()
            if workspace_root is not None
            else self.project_root
        )
        self.inventory = inventory

        self.kernel_root = (
            self.project_root / "section_1_central_mind"
        ).resolve()
        self.constitution_root = (
            self.project_root / "section_2_constitution"
        ).resolve()
        self.memory_root = (
            self.project_root / "section_3_memory"
        ).resolve()
        self.workspace_root = (
            self.project_root / "section_10_workspace"
        ).resolve()
        self.data_root = (
            self.project_root / "section_9_data"
        ).resolve()
        self.runtime_root = (
            self.project_root / ".central_mind"
        ).resolve()

        self._component_roots = self._build_component_roots()

    @staticmethod
    def _is_within(path: Path, parent: Path) -> bool:
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False

    def _build_component_roots(self):
        roots = []

        for info in self.inventory.all():
            root = Path(info.path).resolve()

            if not self._is_within(root, self.project_root):
                raise ValueError(
                    f"Inventory component escapes project root: {root}"
                )

            roots.append((
                root,
                str(info.name),
                str(info.kind),
            ))

        # Longest path first so a future nested registered component cannot
        # accidentally be attributed to a broader parent component.
        roots.sort(
            key=lambda item: len(item[0].parts),
            reverse=True,
        )

        return tuple(roots)

    def _semantic_roots(self):
        """Return trusted semantic roots known to this classifier.

        This is derived from the same authoritative roots used by classify().
        It is not a second ownership registry and makes no authorization
        decision.
        """
        roots = [
            self.kernel_root,
            self.constitution_root,
            self.memory_root,
            self.runtime_root,
            self.workspace_root,
            self.data_root,
        ]

        roots.extend(
            owner_root
            for owner_root, _owner_name, _owner_kind
            in self._component_roots
        )

        # Deduplicate canonical paths while preserving deterministic order.
        unique = {
            str(path): path
            for path in roots
        }

        return tuple(
            sorted(
                unique.values(),
                key=lambda path: (
                    len(path.parts),
                    str(path),
                ),
            )
        )

    def boundaries_within(
        self,
        resource: ResourceDescriptor,
        scope: str,
    ) -> tuple[ResourceDescriptor, ...]:
        """Describe trusted semantic roots crossed by a scoped resource.

        This method answers only what additional semantic resource roots lie
        inside the requested reach. It grants no authority.

        exact
            Reaches only the named resource, so there are no descendant
            boundaries.

        children
            Reports semantic roots that are immediate children of the named
            filesystem resource.

        tree
            Reports every semantic root recursively contained beneath the
            named filesystem resource.

        The starting resource itself is never returned as a crossed boundary.
        """
        if not isinstance(resource, ResourceDescriptor):
            raise TypeError("resource must be a ResourceDescriptor")

        if scope not in {"exact", "children", "tree"}:
            raise ValueError(
                f"unsupported filesystem boundary scope: {scope!r}"
            )

        if scope == "exact":
            return ()

        start = Path(resource.path).resolve()

        # External resources have no trusted project semantic descendants.
        if resource.kind == "external":
            return ()

        found = []

        for semantic_root in self._semantic_roots():
            semantic_root = semantic_root.resolve()

            if semantic_root == start:
                continue

            if not self._is_within(semantic_root, start):
                continue

            relative = semantic_root.relative_to(start)

            if scope == "children" and len(relative.parts) != 1:
                continue

            descriptor = self.classify(semantic_root)

            # A root that classifies identically to the starting descriptor
            # is not a semantic boundary crossing.
            same_identity = (
                descriptor.kind == resource.kind
                and descriptor.owner_kind == resource.owner_kind
                and descriptor.owner_name == resource.owner_name
                and descriptor.owner_root == resource.owner_root
            )

            if same_identity:
                continue

            found.append(descriptor)

        # A broad semantic root can contain narrower registered roots.
        # Keep each distinct boundary because authorization may differ.
        unique = {}

        for descriptor in found:
            unique[str(descriptor.path)] = descriptor

        return tuple(
            unique[key]
            for key in sorted(
                unique,
                key=lambda value: (
                    len(Path(value).parts),
                    value,
                ),
            )
        )

    def classify(
        self,
        target: str | Path,
        *,
        base: Optional[Path] = None,
    ) -> ResourceDescriptor:
        candidate = Path(target)

        if not candidate.is_absolute():
            anchor = (
                Path(base).resolve()
                if base is not None
                else self.project_root
            )
            candidate = anchor / candidate

        resolved = candidate.resolve()

        if not self._is_within(
            resolved,
            self.authorized_workspace_root,
        ):
            return ResourceDescriptor(
                kind="external",
                path=resolved,
            )

        if not self._is_within(resolved, self.project_root):
            return ResourceDescriptor(
                kind="workspace",
                path=str(resolved),
                relative_path=str(
                    resolved.relative_to(
                        self.authorized_workspace_root
                    )
                ),
            )

        relative = str(resolved.relative_to(self.project_root))

        # Protected semantic roots take precedence over generic ownership.
        if self._is_within(resolved, self.kernel_root):
            return ResourceDescriptor(
                kind="kernel",
                path=resolved,
                relative_path=relative,
            )

        if self._is_within(resolved, self.constitution_root):
            return ResourceDescriptor(
                kind="constitution",
                path=resolved,
                relative_path=relative,
            )

        if self._is_within(resolved, self.memory_root):
            return ResourceDescriptor(
                kind="memory",
                path=resolved,
                relative_path=relative,
            )

        if self._is_within(resolved, self.runtime_root):
            return ResourceDescriptor(
                kind="runtime_state",
                path=resolved,
                relative_path=relative,
            )

        for owner_root, owner_name, owner_kind in self._component_roots:
            if self._is_within(resolved, owner_root):
                return ResourceDescriptor(
                    kind="component",
                    path=resolved,
                    relative_path=relative,
                    owner_name=owner_name,
                    owner_kind=owner_kind,
                    owner_root=str(
                        owner_root.relative_to(self.project_root)
                    ),
                )

        if self._is_within(resolved, self.workspace_root):
            return ResourceDescriptor(
                kind="workspace",
                path=resolved,
                relative_path=relative,
            )

        if self._is_within(resolved, self.data_root):
            return ResourceDescriptor(
                kind="data",
                path=resolved,
                relative_path=relative,
            )

        # Project files that are not one of the semantic roots above remain
        # ordinary project/workspace resources. This includes the app,
        # capabilities, top-level files, and future unregistered areas.
        return ResourceDescriptor(
            kind="workspace",
            path=resolved,
            relative_path=relative,
        )
