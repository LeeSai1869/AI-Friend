"""Write code changes."""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path
from typing import Any, Dict


class Writer:

    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def write(self, prompt: str) -> Dict[str, Any]:
        try:
            reply = self._call_ollama(prompt)
        except Exception as exc:
            return {"text": f"[coder unavailable: {exc}]"}

        file_path = self._extract_file_path(reply)
        code = self._extract_code(reply)

        if not file_path or not code:
            return {"text": reply, "file": None}

        target = (self.root / file_path).resolve()
        if not str(target).startswith(str(self.root)):
            return {"text": reply, "file": None, "error": "path escapes root"}

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(code, encoding="utf-8")
        return {"text": reply, "file": str(target)}

    def _call_ollama(self, prompt: str) -> str:
        payload = {
            "model": "qwen2.5-coder:7b",
            "messages": [
                {"role": "system", "content":
                    "You write code. When you write a file, use the format:\n"
                    "FILE: path/to/file.py\n"
                    "```python\n...code...\n```"},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {"num_predict": 2000},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "http://localhost:11434/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=240) as resp:
            parsed = json.loads(resp.read().decode("utf-8"))
            return parsed.get("message", {}).get("content", "")

    def _extract_file_path(self, text: str) -> str | None:
        m = re.search(r"FILE:\s*([^\n]+)", text)
        if m:
            return m.group(1).strip()
        return None

    def _extract_code(self, text: str) -> str | None:
        m = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
        if m:
            return m.group(1)
        return None