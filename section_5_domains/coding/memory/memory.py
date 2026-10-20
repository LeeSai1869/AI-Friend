"""Coding Project local memory.

This is project orientation/context, not Section 3 permanent Memory.
Nothing here may directly mutate AI Friend permanent Memory.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..workspace import CodingWorkspace


class ProjectMemory:
    RELATIVE_PATH = Path(".ai-friend/project-memory.json")

    def __init__(self, workspace: CodingWorkspace):
        self.workspace = workspace

    @property
    def path(self) -> Path:
        return self.workspace.resolve(self.RELATIVE_PATH)

    def read(self) -> dict:
        if not self.path.exists():
            return {}

        try:
            value = json.loads(
                self.path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return {}

        return value if isinstance(value, dict) else {}

    def prepare_write(self, value: dict) -> dict:
        """Describe a desired update without performing filesystem mutation.

        Actual writes must later go through the guarded Coding tool path.
        """
        if not isinstance(value, dict):
            raise TypeError("project memory must be a mapping")

        return {
            "path": self.RELATIVE_PATH.as_posix(),
            "content": json.dumps(
                value,
                indent=2,
                ensure_ascii=False,
            ) + "\n",
        }
