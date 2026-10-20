"""Plan a code change."""
from __future__ import annotations

from typing import Any, Dict


class Planner:

    def plan(self, prompt: str) -> str:
        try:
            mod = __import__("engine", fromlist=["ORGAN"])
            # fall through — prefer reasoner via mind
            raise ImportError
        except Exception:
            pass
        try:
            reasoner = __import__("engine", fromlist=["ORGAN"]).ORGAN
        except Exception:
            reasoner = None
        # Direct call for now
        try:
            import json, urllib.request
            payload = {
                "model": "deepseek-r1:14b",
                "messages": [
                    {"role": "system", "content": "You are a careful planner."},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "options": {"num_predict": 800},
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                "http://localhost:11434/api/chat",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                parsed = json.loads(resp.read().decode("utf-8"))
                return parsed.get("message", {}).get("content", "")
        except Exception as exc:
            return f"[planner unavailable: {exc}]"