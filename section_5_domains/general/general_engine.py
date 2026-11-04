"""General domain. Handles open-ended requests with plain responses."""
from __future__ import annotations

from pathlib import Path
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

    SELF_DESCRIPTION = Path(__file__).with_name("self_description.md")
    SELF_DESCRIPTION_LIMIT = 8000

    def handle_consultation(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Return bounded, read-only evidence describing AI Friend itself."""
        consultation = request.get("consultation") or {}
        if not isinstance(consultation, dict):
            return {"status": "error", "error": "consultation payload must be a mapping"}
        capability = str(
            consultation.get("capability")
            or request.get("evidence_capability")
            or ""
        ).strip()
        if capability != "app_self_description":
            return {
                "status": "error",
                "error": "unsupported General evidence capability: " + repr(capability),
            }
        try:
            text = self.SELF_DESCRIPTION.read_text(encoding="utf-8")
        except OSError as exc:
            return {"status": "error", "error": "self description unavailable: " + str(exc)}
        return {
            "status": "ok",
            "evidence": {
                "capability": capability,
                "kind": "curated_description",
                "authority": "curated summary of AI Friend; the Constitution governs and live state comes from other evidence",
                "truncated": len(text) > self.SELF_DESCRIPTION_LIMIT,
                "content": text[: self.SELF_DESCRIPTION_LIMIT],
            },
        }


ORGAN = GeneralOrgan()