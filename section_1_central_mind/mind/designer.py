"""The Designer.

Reads the actual code. Produces section_2_constitution/design_actual.md.
Mechanical. Deterministic. No language model involved.

Watches the architecture. When .py or manifest files change, the
document regenerates. Data files (memory entries, chat logs) do not
trigger regeneration and are not included in the document.
"""
from __future__ import annotations

import ast
import hashlib
import threading
import time
from pathlib import Path
from typing import Any, Dict, List


WATCH_INTERVAL = 30

# Only these sections are part of the design.
INCLUDED_SECTIONS = {
    "section_0_app",
    "section_1_central_mind",
    "section_2_constitution",
    "section_3_memory",
    "section_4_chatbox",
    "section_5_domains",
    "section_6_capabilities",
    "section_7_models",
    "section_8_tools",
    "section_10_workspace",
}

# Files with these extensions are included if inside an included section.
INCLUDED_EXTS = {".py", ".js", ".ts", ".json", ".html", ".css", ".rs", ".md"}

# Never walk into these directories.
IGNORED_DIRS = {
    ".git", ".venv", "venv", "__pycache__", ".central_mind",
    "node_modules", ".mypy_cache", ".pytest_cache", ".next",
    "dist", "build", "target", "entries", "chats",
    ".DS_Store",
}

# Extensions that count as "architecture" for the hash.
WATCHED_EXTS = {".py", ".js", ".ts", ".rs"}

OUTPUT_PATH = Path("section_2_constitution/design_actual.md")


class Designer:

    def __init__(self, workspace_root: Path, logger=None):
        self.workspace_root = Path(workspace_root).resolve()
        self.logger = logger or (lambda msg: print(msg))
        self._stop = threading.Event()
        self._last_hash = ""
        self._thread = None

    # ---- path inclusion rules ------------------------------------

    def _is_included(self, path: Path) -> bool:
        try:
            rel = path.relative_to(self.workspace_root)
        except ValueError:
            return False
        if len(rel.parts) < 2:
            # A file at the project root. Not part of any section.
            return False
        top = rel.parts[0]
        if top not in INCLUDED_SECTIONS:
            return False
        if any(part in IGNORED_DIRS for part in rel.parts):
            return False
        if path.name.startswith("."):
            return False
        if path.suffix.lower() not in INCLUDED_EXTS:
            return False
        return True

    # ---- hash ----------------------------------------------------

    def _hash_architecture(self) -> str:
        h = hashlib.sha256()
        for path in sorted(self.workspace_root.rglob("*")):
            if not path.is_file():
                continue
            if not self._is_included(path):
                continue
            if path.suffix.lower() not in WATCHED_EXTS and path.name != "__manifest__.py":
                continue
            try:
                data = path.read_bytes()
            except Exception:
                continue
            rel = str(path.relative_to(self.workspace_root))
            h.update(rel.encode("utf-8"))
            h.update(b"\x00")
            h.update(data)
            h.update(b"\x00")
        return h.hexdigest()

    # ---- parse one file ------------------------------------------

    def _parse_python(self, path: Path) -> Dict[str, Any]:
        try:
            src = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return {"error": str(e)}
        try:
            tree = ast.parse(src)
        except SyntaxError as e:
            return {"error": f"syntax error: {e}"}

        imports: List[str] = []
        classes: List[Dict[str, Any]] = []
        functions: List[str] = []

        for node in tree.body:
            if isinstance(node, ast.Import):
                for a in node.names:
                    imports.append(a.name)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                classes.append({"name": node.name, "methods": methods})
            elif isinstance(node, ast.FunctionDef):
                functions.append(node.name)

        return {
            "imports": imports,
            "classes": classes,
            "functions": functions,
            "lines": len(src.splitlines()),
        }

    # ---- build the document --------------------------------------

    def build(self) -> str:
        sections: Dict[str, List[Path]] = {}
        for path in sorted(self.workspace_root.rglob("*")):
            if not path.is_file():
                continue
            if not self._is_included(path):
                continue
            rel = path.relative_to(self.workspace_root)
            top = rel.parts[0]
            sections.setdefault(top, []).append(path)

        lines: List[str] = []
        lines.append("# Actual Design - AI Friend V1")
        lines.append("")
        lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("Source: mechanical analysis of code (no model)")
        lines.append("")
        lines.append("This document describes the actual current state of the code.")
        lines.append("It regenerates automatically when architecture changes.")
        lines.append("It is not a specification. For requirements, see each")
        lines.append("section's requirements.md.")
        lines.append("")

        for section_name in sorted(sections.keys()):
            files = sections[section_name]
            py_files = [f for f in files if f.suffix == ".py"]
            js_files = [f for f in files if f.suffix in {".js", ".ts"}]
            md_files = [f for f in files if f.suffix == ".md"]
            rs_files = [f for f in files if f.suffix == ".rs"]
            other_files = [f for f in files
                           if f.suffix not in {".py", ".js", ".ts", ".rs", ".md"}]

            lines.append(f"## {section_name}")
            lines.append("")
            lines.append(f"Total files: {len(files)}  "
                         f"(.py: {len(py_files)}, .js/.ts: {len(js_files)}, "
                         f".rs: {len(rs_files)}, .md: {len(md_files)}, "
                         f"other: {len(other_files)})")
            lines.append("")

            if py_files:
                lines.append("### Python modules")
                lines.append("")
                for f in py_files:
                    rel = f.relative_to(self.workspace_root)
                    info = self._parse_python(f)
                    if "error" in info:
                        lines.append(f"- `{rel}` - {info['error']}")
                        continue
                    lines.append(f"- `{rel}` ({info['lines']} lines)")
                    if info["imports"]:
                        lines.append(f"  - imports: {', '.join(info['imports'][:8])}")
                    for cls in info["classes"]:
                        methods = ", ".join(cls["methods"][:8])
                        lines.append(f"  - class `{cls['name']}`: {methods}")
                    if info["functions"]:
                        lines.append(f"  - functions: {', '.join(info['functions'][:8])}")
                lines.append("")

            if js_files:
                lines.append("### JavaScript modules")
                lines.append("")
                for f in js_files[:50]:
                    rel = f.relative_to(self.workspace_root)
                    lines.append(f"- `{rel}`")
                lines.append("")

            if rs_files:
                lines.append("### Rust modules")
                lines.append("")
                for f in rs_files[:50]:
                    rel = f.relative_to(self.workspace_root)
                    lines.append(f"- `{rel}`")
                lines.append("")

            if md_files:
                lines.append("### Documentation")
                lines.append("")
                for f in md_files:
                    rel = f.relative_to(self.workspace_root)
                    lines.append(f"- `{rel}`")
                lines.append("")

            if other_files:
                lines.append("### Other files")
                lines.append("")
                for f in other_files[:20]:
                    rel = f.relative_to(self.workspace_root)
                    lines.append(f"- `{rel}`")
                if len(other_files) > 20:
                    lines.append(f"- ... and {len(other_files) - 20} more")
                lines.append("")

        return "\n".join(lines)

    # ---- write ---------------------------------------------------

    def write(self, content: str) -> Path:
        target = (self.workspace_root / OUTPUT_PATH).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def run_once(self) -> Path:
        self.logger("[designer] regenerating design_actual.md")
        content = self.build()
        return self.write(content)

    # ---- watcher -------------------------------------------------

    def _watch_loop(self) -> None:
        try:
            self._last_hash = self._hash_architecture()
            self.run_once()
        except Exception as e:
            self.logger(f"[designer] initial build failed: {e}")

        while not self._stop.is_set():
            time.sleep(WATCH_INTERVAL)
            try:
                current = self._hash_architecture()
            except Exception as e:
                self.logger(f"[designer] hash error: {e}")
                continue
            if current != self._last_hash:
                self._last_hash = current
                try:
                    self.run_once()
                except Exception as e:
                    self.logger(f"[designer] rebuild failed: {e}")

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        self.logger("[designer] watcher started")

    def stop(self) -> None:
        self._stop.set()
