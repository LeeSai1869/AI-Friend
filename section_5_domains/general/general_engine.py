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
            return {"status": "error", "error": "shared model caller is unavailable"}

        try:
            reply = caller.route(
                domain="chat", capability="answer",
                messages=[{"role": "user", "content": text}],
            )
            return {"status": "ok", "output": reply}
        except Exception as e:
            return {"status": "error", "error": "No conversational model is available; check the configured model service."}


ORGAN = GeneralOrgan()