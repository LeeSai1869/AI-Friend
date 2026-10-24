"""The Questioner.

Asks the user through the chatbox. Knows only the shape of a
question: attribute, options, default. The organ does the rest.
"""
from __future__ import annotations

from typing import Any, Dict, List


class Questionnaire:

    def __init__(self, chatbox):
        """chatbox must expose: ask(question) -> answer"""
        self.chatbox = chatbox

    def ask(self, questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        answers: Dict[str, Any] = {}
        for q in questions:
            attribute = q.get("attribute")
            if not attribute:
                continue
            try:
                answer = self.chatbox.ask(q)
            except Exception:
                answer = q.get("default")
            answers[attribute] = answer
        return answers
        

Questioner = Questionnaire
