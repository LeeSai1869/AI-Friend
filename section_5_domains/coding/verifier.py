"""Verify a coding change."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


class Verifier:

    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def verify(self, plan: str, code: Dict[str, Any], test: Dict[str, Any]) -> Dict[str, Any]:
        if not code.get("file"):
            return {"ok": False, "reason": "no file was written"}
        if not test.get("ok", False):
            return {"ok": False, "reason": f"tests failed: {test.get('reason', '')[:200]}"}
        return {"ok": True, "reason": "file written and executed successfully"}