"""Neutral path helpers shared by tools.

This module performs path resolution/containment needed to describe and
execute filesystem effects. It contains no authorization policy.

Authorization belongs to Central Mind's Guard layer.
"""
from __future__ import annotations

from pathlib import Path


def missing_parent_directories(
    workspace_root: Path,
    target: str | Path,
) -> tuple[Path, ...]:
    """Return missing parent directories from highest to lowest.

    The target itself is excluded. Existing symlinks are resolved before
    containment is checked, so a path cannot use a symlink to escape the
    workspace.

    This helper describes filesystem mutations; it does not authorize them.
    """
    root = Path(workspace_root).resolve()
    candidate = Path(target)

    if not candidate.is_absolute():
        candidate = root / candidate

    resolved = candidate.resolve()

    if resolved != root and root not in resolved.parents:
        raise ValueError(
            f"path escapes workspace: {target}"
        )

    parent = resolved.parent
    missing = []

    while (
        parent != root
        and root in parent.parents
        and not parent.exists()
    ):
        missing.append(parent)
        parent = parent.parent

    missing.reverse()
    return tuple(missing)
