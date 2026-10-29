"""The chatbox — the mind's tongue.

This is the simple interface the mind uses to talk to the user.
It is NOT the chat container (that is chat.py).

The chatbox does three things:
  - ask(question)      -> a string (the user's answer)
  - notify(message)    -> display a system message
  - present(response)  -> display the mind's final response
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List


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

    def render_for_review(
        self,
        *,
        objective: str,
        communication_intent: Dict[str, Any],
        verified_evidence: List[Any],
        request_model: Callable[[List[Dict[str, str]]], Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Draft user-facing language through Chat's model capability."""
        import json

        draft = request_model([
            {
                "role": "system",
                "content": (
                    "Write in the first person, speaking directly to the person who asked. "
                    "Answer their request using only the verified evidence provided, and reply in the language they wrote in. "
                    "Never mention drafts, review, approval, Central Mind or the evidence format. "
                    "When execution_receipts report files already written, report those actions in the past tense. "
                    "Do not offer to provide them and do not generate replacement source code. "
                    "Only discuss actual file contents if those contents are in the supplied evidence. "
                    "Do not state what you can or cannot do unless the evidence says so. "
                    "If the evidence does not contain what is needed, say plainly which information you do not have and what the person could provide. "
                    "Do not invent actions, files, artifacts, test results or certainty, and preserve any failures or limitations the evidence reports. "
                    "If communication_intent contains reviewer_feedback, correct exactly those problems, or say plainly what you are unsure about."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({
                    "objective": objective,
                    "communication_intent": communication_intent,
                    "verified_evidence": verified_evidence,
                }, ensure_ascii=False, default=str),
            },
        ])
        if isinstance(draft, dict):
            subjects = [e.get("subject") for e in verified_evidence if isinstance(e, dict)][:8]
            try:
                import os
                import time
                from pathlib import Path
                directory = Path(os.environ.get("AI_FRIEND_STATE_DIR") or ".").expanduser() / "debug"
                directory.mkdir(parents=True, exist_ok=True)
                record = {
                    "ts": round(time.time(), 3),
                    "ok": draft.get("ok"),
                    "model": draft.get("model"),
                    "evidence_count": len(verified_evidence),
                    "evidence_subjects": subjects,
                    "evidence": json.dumps(verified_evidence, ensure_ascii=False, default=str)[:3000],
                    "draft": str(draft.get("output", ""))[:800],
                    "attempts": draft.get("attempts"),
                }
                with (directory / "chat_render.jsonl").open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
            except Exception as exc:
                print(f"[chat-debug] could not write render record: {exc}")
        return draft

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