"""The Tool interface.

Every tool is a small class that declares what it does and how to
call it. Tools are discovered automatically from section_8_tools.
Adding a tool is adding a folder. This base class never changes.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from guard.contract import ToolEffect


class Tool:
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}

    def __init__(self, workspace_root: Path, broker):
        self.workspace_root = Path(workspace_root).resolve()
        self.broker = broker

    def effects(
        self,
        args: Dict[str, Any],
    ) -> tuple[ToolEffect, ...]:
        """Describe intended effects before execution.

        Every concrete tool operation must implement this socket before
        guarded execution is enabled. The base implementation fails closed.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not declare effects"
        )

    def call(self, args: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def _resolve(self, relative: str) -> Path:
        target = (self.workspace_root / relative).resolve()
        if target != self.workspace_root and self.workspace_root not in target.parents:
            raise ValueError(f"path escapes workspace: {relative}")
        return target
