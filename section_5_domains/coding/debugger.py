"""Diagnose failures."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


class Debugger:

    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def diagnose(self, error_text: str) -> Dict[str, Any]:
        # Simple heuristic — real diagnosis is done by the reasoner model.
        lines = error_text.strip().splitlines()
        if not lines:
            return {"ok": False, "reason": "empty error"}
        return {"ok": True, "reason": f"last line: {lines[-1]}"}