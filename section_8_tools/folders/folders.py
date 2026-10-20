"""The folders tool. Creates empty folders inside the workspace."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from _base.tool import Tool
from _base.paths import missing_parent_directories
from guard.contract import ToolEffect


class CreateFolder(Tool):
    name = "create_folder"
    description = "Create an empty folder (and any parent folders) inside the workspace."
    parameters = {"path": "relative path from workspace root"}

    def effects(self, args: Dict[str, Any]) -> tuple[ToolEffect, ...]:
        rel = (args.get("path") or "").strip()
        if not rel:
            raise ValueError("path is required")
        target = self._resolve(rel)

        effects = [
            ToolEffect(
                action="create",
                target=str(parent),
                scope="exact",
            )
            for parent in missing_parent_directories(
                self.workspace_root,
                target,
            )
        ]

        effects.append(
            ToolEffect(
                action="create",
                target=str(target),
                scope="exact",
            )
        )

        return tuple(effects)

    def call(self, args: Dict[str, Any]) -> Dict[str, Any]:
        rel = (args.get("path") or "").strip()
        if not rel:
            return {"ok": False, "data": None, "error": "path is required"}
        if rel.startswith("section_0_central_mind") or rel.startswith("section_1_central_mind"):
            return {"ok": False, "data": None, "error": "refused: cannot create inside the kernel"}
        try:
            target = self._resolve(rel)
        except ValueError as e:
            return {"ok": False, "data": None, "error": str(e)}
        if target.exists():
            return {"ok": True, "data": {"path": rel, "created": False, "note": "already exists"}, "error": None}
        try:
            target.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return {"ok": False, "data": None, "error": str(e)}
        return {"ok": True, "data": {"path": rel, "created": True}, "error": None}


TOOLS = [CreateFolder]
