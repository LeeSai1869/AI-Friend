"""The Router.

Given a request and the inventory, choose which organs to call.
No hard-coded domain names. The router reads keywords from the
inventory and scores each organ against the request.
"""
from __future__ import annotations

from typing import Dict, List

from .inventory import Inventory, OrganInfo


class Router:

    def __init__(self, inventory: Inventory, max_organs: int = 3):
        self.inventory = inventory
        self.max_organs = max_organs

    def route(self, request: Dict) -> List[OrganInfo]:
        text = (request.get("text") or "").lower()
        if not text:
            return self._fallback()

        scored = []
        for organ in self.inventory.all():
            score = self._score(organ, text)
            if score > 0:
                scored.append((score, organ))

        if not scored:
            return self._fallback()

        scored.sort(key=lambda x: -x[0])
        top = scored[0][0]
        winners = [o for s, o in scored if s == top]
        return winners[: self.max_organs]

    def _score(self, organ: OrganInfo, text: str) -> int:
        import re
        words = set(re.findall(r"[a-z0-9_]+", text.lower()))
        score = 0
        for kw in organ.keywords:
            if kw.lower() in words:
                score += 1
        for cap in organ.capabilities:
            # Match multi-word capabilities by substring, single by word.
            cap_lower = cap.lower()
            if "_" in cap_lower or " " in cap_lower:
                if cap_lower in text:
                    score += 1
            else:
                if cap_lower in words:
                    score += 1
        return score

    def _fallback(self):
        # Prefer the chat model for general questions.
        chat = self.inventory.get("chat")
        if chat is not None:
            return [chat]
        # Otherwise any model.
        for organ in self.inventory.all():
            if organ.kind == "model":
                return [organ]
        # Never fall back to a tool or a domain — those require
        # explicit keyword match.
        return []