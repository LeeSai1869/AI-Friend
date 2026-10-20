"""Track and (later) generate capabilities.

For MVP this only lists and registers capabilities. Self-created
capabilities go under capabilities/generated/<name>/ and are not
allowed to modify the constitution.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List


class CapabilityManager:
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.generated_dir = self.project_root / "capabilities" / "generated"
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        self._builtin: Dict[str, str] = {
            "inspect_workspace": "coding.inspector",
            "write_file": "coding.writer",
            "run_python": "coding.tester",
            "verify_files": "coding.verifier",
        }

    def names(self) -> List[str]:
        generated = [
            p.name for p in self.generated_dir.iterdir() if p.is_dir()
        ]
        return sorted(set(self._builtin.keys()) | set(generated))

    def register(self, name: str, spec: str) -> None:
        self._builtin[name] = spec