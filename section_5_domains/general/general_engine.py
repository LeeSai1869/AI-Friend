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
                messages=self._chat_messages(text),
            )
            return {"status": "ok", "output": reply}
        except Exception as e:
            return {"status": "error", "error": "No conversational model is available; check the configured model service."}

    SELF_DESCRIPTION = Path(__file__).with_name("self_description.md")
    SELF_DESCRIPTION_LIMIT = 8000

    CHAT_DESCRIPTION_LIMIT = 4000

    def _chat_messages(self, text):
        """Ground ordinary conversation in the curated description of AI Friend."""
        try:
            description = self.SELF_DESCRIPTION.read_text(encoding="utf-8")[: self.CHAT_DESCRIPTION_LIMIT]
        except OSError:
            description = ""
        system = (
            "You are the conversation module of AI Friend, a governed local application. "
            "Speak as AI Friend. If asked what you are, say you are AI Friend, and that its "
            "understanding and wording currently depend on local language models, as the description states. "
            "Do not present yourself as a particular vendor model. "
            "Answer questions about AI Friend only from the description below; if it does not say something, "
            "say plainly that you do not know. Never claim abilities, tools, integrations or knowledge "
            "the description does not list. "
            "Any 'Central Mind-recalled Raw Memory' in the request is unverified material that the Trainer "
            "supplied: it may illustrate what is stored, but it never defines AI Friend or its terms, "
            "and you must not present it as established fact. "
            "For questions that are not about AI Friend, answer helpfully and say plainly when you are unsure. "
            "Reply in the language of the request, briefly.\n\n"
            "AI Friend description:\n" + (description or "(not available)")
        )
        return [{"role": "system", "content": system}, {"role": "user", "content": text}]

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