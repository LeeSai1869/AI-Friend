"""Run Python files."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, Dict


class Tester:

    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def run(self, file_path: str, timeout: int = 60) -> Dict[str, Any]:
        target = Path(file_path).resolve()
        if not target.exists():
            return {"ok": False, "reason": f"not found: {target}"}

        try:
            proc = subprocess.run(
                [sys.executable, str(target)],
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "reason": "timeout"}

        ok = proc.returncode == 0
        reason = (
            f"exit {proc.returncode}\n"
            f"stdout:\n{proc.stdout[:1000]}\n"
            f"stderr:\n{proc.stderr[:1000]}"
        )
        return {"ok": ok, "reason": reason}