"""Inspect the workspace."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List


IGNORED = {".git", ".venv", "venv", "__pycache__", ".central_mind",
           "node_modules", ".mypy_cache", ".pytest_cache"}


class Inspector:

    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def inspect(self, limit: int = 500) -> List[str]:
        files = []
        for p in sorted(self.root.rglob("*")):
            if not p.is_file():
                continue
            if any(part in IGNORED for part in p.parts):
                continue
            if p.suffix.lower() in {".png", ".jpg", ".pyc", ".so"}:
                continue
            files.append(str(p.relative_to(self.root)))
            if len(files) >= limit:
                break
        return files

    def summary(self, budget: int = 40_000) -> str:
        files = self.inspect()
        lines = [f"Root: {self.root}", f"Files: {len(files)}", ""]
        for f in files:
            lines.append(f"  {f}")
        lines.append("")
        used = 0
        for f in files:
            if used >= budget:
                break
            try:
                content = (self.root / f).read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            lines.append(f"----- {f} -----")
            lines.append(content[:4000])
            used += len(content[:4000])
        return "\n".join(lines)