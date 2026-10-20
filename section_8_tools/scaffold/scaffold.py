"""Scaffold tools.

A scaffold is a pre-written set of directories and files,
stored as a folder under section_10_workspace/scaffolds/.

Each scaffold folder contains:
  - scaffold.json   - describes dirs and files, with sources
  - sources/        - the actual file contents

Tools:
  list_scaffolds  - list available scaffolds
  read_scaffold   - read one scaffold's description
  apply_scaffold  - apply one scaffold: create all dirs and files
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from _base.tool import Tool
from guard.contract import ToolEffect
from _base.paths import missing_parent_directories


SCAFFOLDS_DIR = Path("section_10_workspace/scaffolds")


class _ScaffoldBase(Tool):
    """Shared helpers for scaffold tools."""

    def _scaffolds_root(self) -> Path:
        return (self.workspace_root / SCAFFOLDS_DIR).resolve()


class ListScaffolds(_ScaffoldBase):
    name = "list_scaffolds"
    description = "List available scaffolds in section_10_workspace/scaffolds/."
    parameters = {}

    def effects(self, args: Dict[str, Any]) -> tuple[ToolEffect, ...]:
        return (
            ToolEffect(
                action="read",
                target=str(self._scaffolds_root()),
                scope="tree",
            ),
        )

    def call(self, args: Dict[str, Any]) -> Dict[str, Any]:
        root = self._scaffolds_root()
        if not root.exists():
            return {"ok": True, "data": {"scaffolds": []}, "error": None}

        results = []
        for folder in sorted(root.iterdir()):
            if not folder.is_dir():
                continue
            if folder.name.startswith("."):
                continue
            manifest = folder / "scaffold.json"
            if not manifest.exists():
                continue
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except Exception as e:
                results.append({
                    "name": folder.name,
                    "error": f"invalid scaffold.json: {e}",
                })
                continue
            results.append({
                "name": data.get("name", folder.name),
                "description": data.get("description", ""),
                "dir_count": len(data.get("dirs", [])),
                "file_count": len(data.get("files", [])),
            })
        return {"ok": True, "data": {"scaffolds": results}, "error": None}


class ReadScaffold(_ScaffoldBase):
    name = "read_scaffold"
    description = "Read the full description of a scaffold by name."
    parameters = {"name": "the scaffold folder name"}

    def effects(self, args: Dict[str, Any]) -> tuple[ToolEffect, ...]:
        name = (args.get("name") or "").strip()
        if not name:
            raise ValueError("name is required")

        manifest = (
            self._scaffolds_root()
            / name
            / "scaffold.json"
        ).resolve()

        return (
            ToolEffect(
                action="read",
                target=str(manifest),
                scope="exact",
            ),
        )

    def call(self, args: Dict[str, Any]) -> Dict[str, Any]:
        name = (args.get("name") or "").strip()
        if not name:
            return {"ok": False, "data": None, "error": "name is required"}

        root = self._scaffolds_root()
        manifest = root / name / "scaffold.json"
        if not manifest.exists():
            return {"ok": False, "data": None, "error": f"scaffold not found: {name}"}

        try:
            text = manifest.read_text(encoding="utf-8")
            data = json.loads(text)
        except Exception as e:
            return {"ok": False, "data": None, "error": f"invalid scaffold.json: {e}"}

        return {"ok": True, "data": {"name": name, "scaffold": data, "raw": text}, "error": None}


class ApplyScaffold(_ScaffoldBase):
    name = "apply_scaffold"
    description = (
        "Apply a scaffold: create all directories and write all files. "
        "Uses sources/ folder for file contents. Refuses to overwrite "
        "existing files unless the scaffold says overwrite=true."
    )
    parameters = {"name": "the scaffold folder name"}

    def effects(self, args: Dict[str, Any]) -> tuple[ToolEffect, ...]:
        name = (args.get("name") or "").strip()
        if not name:
            raise ValueError("name is required")

        scaffold_dir = (
            self._scaffolds_root() / name
        ).resolve()
        manifest_path = scaffold_dir / "scaffold.json"

        if not manifest_path.exists():
            raise ValueError(
                f"scaffold not found: {name}"
            )

        try:
            data = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )
        except Exception as e:
            raise ValueError(
                f"invalid scaffold.json: {e}"
            )

        effects = [
            ToolEffect(
                action="read",
                target=str(manifest_path),
                scope="exact",
            ),
            ToolEffect(
                action="read",
                target=str(scaffold_dir / "sources"),
                scope="tree",
            ),
        ]

        declared_creates = set()

        def add_create(path: Path) -> None:
            resolved = path.resolve()
            key = str(resolved)

            if key in declared_creates:
                return

            declared_creates.add(key)
            effects.append(
                ToolEffect(
                    action="create",
                    target=key,
                    scope="exact",
                )
            )

        for rel in data.get("dirs", []):
            if not isinstance(rel, str) or not rel:
                raise ValueError(
                    "invalid scaffold directory destination"
                )

            target = self._resolve(rel)

            for parent in missing_parent_directories(
                self.workspace_root,
                target,
            ):
                add_create(parent)

            add_create(target)

        for item in data.get("files", []):
            if not isinstance(item, dict):
                raise ValueError(
                    "invalid scaffold file entry"
                )

            rel = item.get("path", "")

            if not isinstance(rel, str) or not rel:
                raise ValueError(
                    "scaffold file entry missing path"
                )

            target = self._resolve(rel)

            for parent in missing_parent_directories(
                self.workspace_root,
                target,
            ):
                add_create(parent)

            if target.exists():
                effects.append(
                    ToolEffect(
                        action="write",
                        target=str(target),
                        scope="exact",
                    )
                )
            else:
                add_create(target)

        return tuple(effects)

    def call(self, args: Dict[str, Any]) -> Dict[str, Any]:
        name = (args.get("name") or "").strip()
        if not name:
            return {"ok": False, "data": None, "error": "name is required"}

        root = self._scaffolds_root()
        scaffold_dir = root / name
        manifest_path = scaffold_dir / "scaffold.json"

        if not manifest_path.exists():
            return {"ok": False, "data": None, "error": f"scaffold not found: {name}"}

        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as e:
            return {"ok": False, "data": None, "error": f"invalid scaffold.json: {e}"}

        dirs = data.get("dirs", [])
        files = data.get("files", [])
        sources_dir = scaffold_dir / "sources"

        dirs_created = 0
        files_written = 0
        files_skipped = 0
        errors: List[str] = []

        for d in dirs:
            try:
                target = self._resolve(d)
                if not target.exists():
                    target.mkdir(parents=True, exist_ok=True)
                    dirs_created += 1
            except Exception as e:
                errors.append(f"mkdir {d}: {e}")

        for f in files:
            rel = f.get("path", "")
            src = f.get("source", "")
            overwrite = bool(f.get("overwrite", False))

            if not rel or not src:
                errors.append(f"file entry missing path or source: {f}")
                continue

            source_path = sources_dir / src
            if not source_path.exists():
                errors.append(f"source not found: {src}")
                continue

            try:
                content = source_path.read_text(encoding="utf-8")
            except Exception as e:
                errors.append(f"read source {src}: {e}")
                continue

            try:
                target = self._resolve(rel)

                # .md protection: existing .md files may never be overwritten
                # by a scaffold, regardless of the `overwrite` flag.
                is_md = str(target).lower().endswith(".md")
                if is_md and target.exists():
                    files_skipped += 1
                    continue

                if target.exists() and not overwrite:
                    files_skipped += 1
                    continue

                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                files_written += 1
            except Exception as e:
                errors.append(f"write {rel}: {e}")

        return {
            "ok": len(errors) == 0,
            "data": {
                "name": name,
                "dirs_created": dirs_created,
                "files_written": files_written,
                "files_skipped": files_skipped,
                "errors": errors,
            },
            "error": None if not errors else f"{len(errors)} error(s)",
        }


TOOLS = [ListScaffolds, ReadScaffold, ApplyScaffold]
