"""Filesystem boundary owned by the Coding Domain."""

from __future__ import annotations

from pathlib import Path

from ..project import CodingProject


class CodingWorkspace:
    def __init__(self, project: CodingProject):
        if not isinstance(project, CodingProject):
            raise TypeError("project must be CodingProject")

        self.project = project
        self.root = project.root.resolve()

    def resolve(self, relative: str | Path = "") -> Path:
        candidate = Path(relative)

        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            resolved = (self.root / candidate).resolve()

        if resolved != self.root and self.root not in resolved.parents:
            raise ValueError(
                f"path escapes Coding workspace: {relative}"
            )

        return resolved

    def relative(self, path: str | Path) -> str:
        resolved = self.resolve(path)
        return resolved.relative_to(self.root).as_posix()

    def contains(self, path: str | Path) -> bool:
        try:
            self.resolve(path)
            return True
        except (ValueError, OSError):
            return False
