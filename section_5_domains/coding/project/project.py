"""Coding-owned project identity.

A Coding Project is a domain concept. Central Mind does not own project
identity, project roots, project rules, project history, or project memory.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CodingProject:
    name: str
    root: Path

    @classmethod
    def open(cls, root: str | Path) -> "CodingProject":
        resolved = Path(root).expanduser().resolve()

        if not resolved.exists():
            raise ValueError(f"project does not exist: {resolved}")

        if not resolved.is_dir():
            raise ValueError(f"project is not a directory: {resolved}")

        return cls(
            name=resolved.name or str(resolved),
            root=resolved,
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "root": str(self.root),
        }
