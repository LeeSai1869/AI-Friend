"""Section 4 — Chat.

Chat is AI Friend's universal human communication boundary.

It owns communication mechanics and durable conversational Chat State.
It does not own reasoning, planning, routing, authorization, model
selection, verification, appraisal, learning, or domain semantics.
"""

from .chatbox import Chatbox
from .runtime import ChatRuntime
from .state import Chat, ChatStore, Rejected, Turn, Verified

__all__ = [
    "Chatbox",
    "ChatRuntime",
    "Chat",
    "ChatStore",
    "Turn",
    "Verified",
    "Rejected",
]
