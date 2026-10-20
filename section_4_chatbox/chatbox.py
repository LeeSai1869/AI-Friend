"""The chatbox — the mind's tongue.

This is the simple interface the mind uses to talk to the user.
It is NOT the chat container (that is chat.py).

The chatbox does three things:
  - ask(question)      -> a string (the user's answer)
  - notify(message)    -> display a system message
  - present(response)  -> display the mind's final response
"""
from __future__ import annotations

from typing import Any, Dict


class Chatbox:

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    def ask(self, question: Dict[str, Any]) -> str:
        attribute = question.get("attribute", "?")
        options = question.get("options", [])
        default = question.get("default")

        prompt = f"{attribute}?"
        if options:
            prompt += "  [" + " | ".join(str(o) for o in options) + "]"
        if default is not None:
            prompt += f"  (default: {default})"

        try:
            answer = input(f"  {prompt}\n  > ").strip()
        except EOFError:
            answer = default or ""

        if not answer and default is not None:
            return default
        return answer

    def notify(self, message: str) -> None:
        print()
        print("-- system --")
        print(message)
        print()

    def present(self, response: Any) -> None:
        if isinstance(response, dict):
            status = response.get("status")
            if status == "ok":
                print("Central Mind >")
                print(response.get("output", ""))
            elif status == "needs_answers":
                # The Questioner handles the interactive part.
                pass
            elif status == "error":
                print("Central Mind > [error]")
                print(response.get("errors", []))
            else:
                print("Central Mind >", response)
        else:
            print("Central Mind >", response)

    def tool_status(self, message: str) -> None:
        """Called by the tool loop to report progress."""
        print(f"[tool] {message}")