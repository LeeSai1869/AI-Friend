"""General domain. Handles open-ended requests with plain responses."""
from __future__ import annotations

from typing import Any, Dict

from mind.organ import Organ


class GeneralOrgan(Organ):
    name = "general"
    kind = "domain"
    scope = "outside_guards"
    capabilities = ["chat"]
    keywords = []

    def can_handle(self, request: Dict[str, Any]) -> bool:
        return False

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        text = request.get("text", "")
        caller = request.get("caller")

        if caller is None:
            return {"status": "ok", "output": f"[general] {text}"}

        try:
            reply = caller.call(
                "chat",
                messages=[{"role": "user", "content": text}],
            )
            return {"status": "ok", "output": reply}
        except Exception as e:
            return {"status": "ok", "output": f"[general] {text} (error: {e})"}


ORGAN = GeneralOrgan()