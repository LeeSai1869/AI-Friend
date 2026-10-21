"""Read-only structural view of the active Coding Project."""

from __future__ import annotations

from pathlib import Path

from ..workspace import CodingWorkspace


class ProjectTree:
    """Coding-owned structural map of the currently open project."""

    DEFAULT_IGNORED_DIRECTORIES = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        ".mypy_cache",
        ".pytest_cache",
        ".next",
        "dist",
        "build",
        "target",
    }

    DEFAULT_IGNORED_SUFFIXES = {
        ".pyc", ".pyo", ".so", ".dylib", ".dll", ".exe", ".o",
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico",
        ".zip", ".tar", ".gz", ".dmg",
        ".mp3", ".wav", ".mp4", ".mov",
        ".lock",
    }

    MAX_FILES = 5000

    def __init__(self, workspace: CodingWorkspace):
        self.workspace = workspace

    def _trusted_entry(self, entry: Path):
        try:
            resolved = entry.resolve()
        except OSError:
            return None

        if (
            resolved != self.workspace.root
            and self.workspace.root not in resolved.parents
        ):
            return None

        return resolved

    def list(self, relative: str = "") -> list[dict]:
        target = self.workspace.resolve(relative)

        if not target.exists():
            raise ValueError(f"path does not exist: {relative}")

        if not target.is_dir():
            raise ValueError(f"path is not a directory: {relative}")

        entries = []

        for entry in sorted(
            target.iterdir(),
            key=lambda item: (not item.is_dir(), item.name.lower()),
        ):
            if entry.name.startswith(".") and entry.name != ".ai-friend":
                continue

            if entry.is_dir() and entry.name in self.DEFAULT_IGNORED_DIRECTORIES:
                continue

            resolved = self._trusted_entry(entry)
            if resolved is None:
                continue

            entries.append({
                "name": entry.name,
                "path": resolved.relative_to(self.workspace.root).as_posix(),
                "type": "dir" if entry.is_dir() else "file",
                "text_preview": entry.is_file() and entry.suffix.lower() not in self.DEFAULT_IGNORED_SUFFIXES,
            })

        return entries

    def files(self) -> list[str]:
        """Return the bounded real-file inventory of the open project.

        This is structural project metadata only. Source contents are still
        read through the guarded Coding broker.
        """
        files: list[str] = []
        pending = [""]

        while pending and len(files) < self.MAX_FILES:
            relative = pending.pop(0)

            try:
                entries = self.list(relative)
            except (OSError, ValueError):
                continue

            for entry in entries:
                if entry["type"] == "dir":
                    pending.append(entry["path"])
                elif entry["type"] == "file" and entry.get("text_preview", True):
                    files.append(entry["path"])
                    if len(files) >= self.MAX_FILES:
                        break

        return files
