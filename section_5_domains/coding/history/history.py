"""Coding Project history contract.

History belongs to the project. Mutation is intentionally expressed as a
guarded write proposal; this class does not bypass filesystem tools.
"""

from __future__ import annotations

import json
from pathlib import Path
from time import time

from ..workspace import CodingWorkspace


class ProjectHistory:
    RELATIVE_PATH = Path(".ai-friend/project-history.jsonl")

    def __init__(self, workspace: CodingWorkspace):
        self.workspace = workspace

    @property
    def path(self) -> Path:
        return self.workspace.resolve(self.RELATIVE_PATH)

    def read(self) -> list[dict]:
        if not self.path.exists():
            return []

        records = []

        for line in self.path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines():
            if not line.strip():
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue

            if isinstance(item, dict):
                records.append(item)

        return records

    def prepare_append(
        self,
        event: str,
        *,
        outcome: str = "",
        details: dict | None = None,
    ) -> dict:
        record = {
            "ts": time(),
            "event": str(event),
            "outcome": str(outcome),
            "details": details or {},
        }

        existing = ""
        if self.path.exists():
            existing = self.path.read_text(
                encoding="utf-8",
                errors="replace",
            )

        content = (
            existing
            + json.dumps(record, ensure_ascii=False)
            + "\n"
        )

        return {
            "path": self.RELATIVE_PATH.as_posix(),
            "content": content,
            "record": record,
        }
