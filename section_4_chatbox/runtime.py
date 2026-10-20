"""Section 4 Chat runtime.

This is AI Friend's human communication boundary.

Responsibilities:
- receive a human turn
- own/open durable Chat State
- package available Chat/input observations into generic context
- hand the request to Central Mind
- persist the human turn and any finalized Central Mind response
- return the result to the application surface

It does NOT reason, route, select domains, select models, authorize,
verify, appraise, learn, or interpret domain semantics.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from .state import Chat, ChatStore


class ChatRuntime:
    """Communication boundary between an application surface and Central Mind."""

    def __init__(self, mind: Any, workspace: Path):
        self.mind = mind
        self.workspace = Path(workspace)
        self.store = ChatStore(self.workspace)

    def open_chat(
        self,
        chat_id: Optional[str] = None,
        *,
        domain: str = "general",
    ) -> Chat:
        """Open an existing Chat State or create a new one."""
        if chat_id:
            existing = self.store.load(chat_id)
            if existing is not None:
                return existing

        chat = self.store.create(
            domain=domain,
            topic_lock="off",
        )
        chat.save()
        return chat

    @staticmethod
    def _context_packet(
        *,
        chat: Chat,
        intent: str,
        attachments: List[Dict[str, Any]],
        context: Optional[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        """Build the generic information packet supplied to Central Mind.

        Section 4 records observations; it assigns no semantic meaning or
        authority to producer-specific fields.
        """
        packet: Dict[str, Any] = {
            "source": "chat",
            "chat": chat.load_context(),
            "input": {
                "intent": str(intent or "ask"),
                "attachments": list(attachments),
            },
        }

        if isinstance(context, Mapping):
            packet["observations"] = dict(context)

        return packet

    @staticmethod
    def _final_text(result: Dict[str, Any]) -> str:
        """Read finalized communication without creating or interpreting it."""
        for key in ("text", "output"):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        communication = result.get("communication")
        if isinstance(communication, dict):
            for key in ("text", "output"):
                value = communication.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

        return ""

    def list_chats(self) -> List[Dict[str, Any]]:
        """Return durable Chat State summaries for the application surface."""
        rows: List[Dict[str, Any]] = []

        for chat_id in self.store.list_ids():
            chat = self.store.load(chat_id)
            if chat is None:
                continue

            updated_at = chat.created_at
            if chat.turns:
                updated_at = max(
                    turn.ts for turn in chat.turns
                )

            rows.append({
                "chat_id": chat.chat_id,
                "topic": chat.topic or "(untitled)",
                "domain": chat.domain or "general",
                "created_at": chat.created_at,
                "updated_at": updated_at,
            })

        rows.sort(
            key=lambda row: row.get("updated_at", 0),
            reverse=True,
        )
        return rows

    def load_chat(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """Return one durable Chat State in application-facing form."""
        requested = str(chat_id or "").strip()
        if not requested:
            return None

        chat = self.store.load(requested)
        if chat is None:
            return None

        return {
            "chat_id": chat.chat_id,
            "topic": chat.topic or "New chat",
            "domain": chat.domain or "general",
            "turns": [
                {
                    "role": turn.role,
                    "text": turn.text,
                    "ts": turn.ts,
                    "action": turn.action,
                }
                for turn in chat.turns
            ],
        }

    def respond(
        self,
        text: str,
        *,
        chat_id: Optional[str] = None,
        intent: str = "ask",
        attachments: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Process one human turn through the canonical Chat → Mind boundary."""
        user_text = str(text or "").strip()
        attachment_rows = list(attachments or [])

        if not user_text and not attachment_rows:
            return {
                "ok": False,
                "error": "empty chat request",
            }

        chat = self.open_chat(chat_id)

        if chat.is_first_message() and user_text:
            chat.set_topic(user_text[:240])

        packet = self._context_packet(
            chat=chat,
            intent=intent,
            attachments=attachment_rows,
            context=context,
        )

        try:
            result = self.mind.process(
                user_text,
                context=packet,
            )
        except Exception as exc:
            return {
                "ok": False,
                "chat_id": chat.chat_id,
                "error": f"Central Mind processing failed: {exc}",
            }

        if not isinstance(result, dict):
            return {
                "ok": False,
                "chat_id": chat.chat_id,
                "error": "Central Mind returned a non-mapping result",
            }

        if user_text:
            chat.add_turn(
                "user",
                user_text,
                action=str(intent or "ask"),
            )

        status = str(result.get("status") or "")
        answer = self._final_text(result)

        if answer:
            chat.add_turn(
                "mind",
                answer,
                action="answer",
            )

        chat.update_summary()
        chat.save()

        response: Dict[str, Any] = {
            "ok": status == "ok" and bool(answer),
            "chat_id": chat.chat_id,
            "text": answer,
            "status": status,
            "cognition": result.get("cognition", {}),
        }

        if status == "needs_answers":
            response["questions"] = result.get("questions", [])
            response["error"] = "Central Mind requires additional information"
            return response

        if status == "error":
            response["error"] = str(
                result.get("error")
                or "Central Mind execution failed"
            )
            return response

        if status == "communicate":
            # Communication generation belongs upstream of Chat. Section 4
            # never invokes an LLM or manufactures the answer itself.
            response["ok"] = bool(answer)
            if not answer:
                response["error"] = (
                    "Central Mind requested communication but did not supply "
                    "finalized communication."
                )
            return response

        if status != "ok":
            response["error"] = (
                "Central Mind returned an unknown cognitive status"
            )
            return response

        if not answer:
            response["error"] = (
                "Central Mind completed the turn without finalized output."
            )

        return response
