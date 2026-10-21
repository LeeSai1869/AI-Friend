"""Chat State container owned by Section 4 Chat.

A Chat is a single focused conversation about ONE topic.

It owns:
  - its topic (locked after the first message)
  - its summary (updated every turn)
  - its full turn history
  - its verified solutions (proven to work here)
  - its rejected solutions (proven NOT to work here, with reasons)

It saves everything under:

    .central_mind/chats/<chat_id>/

so a chat can be resumed, audited, or deleted without affecting
any other chat.

The chat is what makes the loop-breaker possible: because the
rejected list is re-read on every turn, the mind cannot silently
drift back into a solution that already failed.
"""
from __future__ import annotations

import json
import time
import uuid
import hashlib
import re
import shutil
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


# ============================================================
# DATA
# ============================================================

@dataclass
class Turn:
    role: str                # "user" | "mind"
    text: str
    ts: float
    action: str = ""         # answer | analyze | work | question
    verified: List[str] = field(default_factory=list)
    rejected: List[str] = field(default_factory=list)


@dataclass
class Rejected:
    solution: str
    reason: str
    context: str
    ts: float


@dataclass
class Verified:
    solution: str
    evidence: str
    ts: float


# ============================================================
# CHAT
# ============================================================

class Chat:
    """A single focused conversation about one topic."""

    def __init__(
        self,
        root: Path,
        chat_id: Optional[str] = None,
        domain: str = "general",
        topic_lock: str = "strict",       # strict | soft | off
    ):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

        self.chat_id = chat_id or self._new_id()
        self.domain = domain
        self.topic_lock = topic_lock

        self.chat_file = self.root / "chat.json"
        self.summary_file = self.root / "summary.md"
        self.turns_file = self.root / "turns.json"
        self.verified_file = self.root / "verified.json"
        self.rejected_file = self.root / "rejected.json"

        # State
        self.topic: str = ""
        self.summary: str = ""
        self.turns: List[Turn] = []
        self.verified: List[Verified] = []
        self.rejected: List[Rejected] = []
        self.pending_clarification: dict = {}
        self.created_at: float = time.time()

        if self.chat_file.exists():
            self.load()

    # --------------------------------------------------------
    # ID
    # --------------------------------------------------------

    @staticmethod
    def _new_id() -> str:
        stamp = time.strftime("%Y_%m_%d_%H%M%S")
        short = uuid.uuid4().hex[:4]
        return f"chat_{stamp}_{short}"

    # --------------------------------------------------------
    # TOPIC
    # --------------------------------------------------------

    def is_first_message(self) -> bool:
        return not self.topic

    def set_topic(self, text: str) -> None:
        """Called once, on the first user message."""
        self.topic = text.strip()
        self.save()

    def check_topic(self, text: str) -> Dict[str, Any]:
        """Decide whether this message belongs to the chat's topic.

        Returns:
          {
            "allowed": bool,
            "reason": str,
            "message": str,   # shown to the user if not allowed
          }
        """
        if self.topic_lock == "off":
            return {"allowed": True, "reason": "topic lock off", "message": ""}

        # First message always allowed; it defines the topic.
        if self.is_first_message():
            return {"allowed": True, "reason": "first message", "message": ""}

        # Heuristic: does the new text share significant words
        # with the topic AND with the recent chat context?
        topic_words = self._words(self.topic)
        context_words = self._words(self._recent_text())
        new_words = self._words(text)

        shared_topic = topic_words & new_words
        shared_context = context_words & new_words

        # If it shares nothing with topic or recent context,
        # it is very likely a new topic.
        looks_new = (not shared_topic) and (not shared_context)

        if not looks_new:
            return {"allowed": True, "reason": "same topic", "message": ""}

        # ---- Not allowed ----

        if self.topic_lock == "strict":
            message = (
                "This chat is about:\n"
                f"  {self.topic}\n\n"
                "That request looks like a different topic.\n"
                "Please start a new chat for it — I will keep\n"
                "this one focused so I do not lose the thread."
            )
            return {"allowed": False, "reason": "new topic", "message": message}

        # soft
        message = (
            "This chat is about:\n"
            f"  {self.topic}\n\n"
            "Your request looks like it might be a new topic.\n"
            "Should I start a new chat, or continue here?"
        )
        return {"allowed": False, "reason": "possible new topic", "message": message}

    @staticmethod
    def _words(text: str) -> set:
        stop = {
            "the", "a", "an", "and", "or", "but", "of", "to", "in",
            "on", "at", "for", "with", "is", "are", "was", "were",
            "be", "been", "this", "that", "it", "i", "you", "we",
            "they", "me", "my", "your", "our", "their", "do", "does",
            "did", "can", "could", "would", "should", "will", "shall",
        }
        return {
            w.strip(".,!?;:\"'()[]{}").lower()
            for w in (text or "").split()
            if len(w) > 2 and w.lower() not in stop
        }

    def _recent_text(self, n: int = 6) -> str:
        recent = self.turns[-n:] if self.turns else []
        return " ".join(t.text for t in recent)

    def model_messages(self, limit: int = 12) -> List[Dict[str, str]]:
        """Return bounded conversational context for a model call.

        Durable Chat State may retain an auditable turn record, but model
        context is deliberately bounded.  Section 3 remains the permanent
        knowledge system; this method does not promote chat text to
        permanent memory.
        """
        messages: List[Dict[str, str]] = []

        for turn in self.turns[-max(1, int(limit)):]:
            role = "assistant" if turn.role == "mind" else "user"
            text = str(turn.text or "").strip()

            if not text:
                continue

            messages.append({
                "role": role,
                "content": text,
            })

        return messages

    # --------------------------------------------------------
    # CONTEXT (re-read before every answer)
    # --------------------------------------------------------

    def load_context(self) -> Dict[str, Any]:
        """What the mind reads before answering.

        This is the heart of the loop-breaker: the rejected list
        is always here, so the mind cannot quietly re-propose a
        solution that already failed.
        """
        return {
            "chat_id": self.chat_id,
            "domain": self.domain,
            "topic": self.topic,
            "summary": self.summary,
            "verified": [asdict(v) for v in self.verified],
            "rejected": [asdict(r) for r in self.rejected],
            "recent_turns": [asdict(t) for t in self.turns[-6:]],
        }

    # --------------------------------------------------------
    # VERIFIED / REJECTED
    # --------------------------------------------------------

    def record_verified(self, solution: str, evidence: str) -> None:
        self.verified.append(
            Verified(solution=solution, evidence=evidence, ts=time.time())
        )
        self._save_verified()
        self.update_summary()

    def record_rejected(self, solution: str, reason: str, context: str = "") -> None:
        self.rejected.append(
            Rejected(
                solution=solution,
                reason=reason,
                context=context,
                ts=time.time(),
            )
        )
        self._save_rejected()
        self.update_summary()

    def find_rejected(self, proposal: str) -> Optional[Dict[str, Any]]:
        """Does this proposal match a previously rejected one?"""
        if not proposal:
            return None

        words = self._words(proposal)
        if not words:
            return None

        best: Optional[Rejected] = None
        best_score = 0

        for item in self.rejected:
            item_words = self._words(item.solution)
            if not item_words:
                continue
            overlap = len(words & item_words)
            score = overlap / max(len(words), 1)
            if score > best_score and score >= 0.6:
                best_score = score
                best = item

        if best is None:
            return None

        return {
            "solution": best.solution,
            "reason": best.reason,
            "context": best.context,
            "ts": best.ts,
        }

    def rejected_message(self, rejected: Dict[str, Any]) -> str:
        return (
            "I have already tried this in this chat.\n\n"
            f"Solution: {rejected['solution']}\n"
            f"Reason it failed: {rejected['reason']}\n"
            f"Context: {rejected.get('context') or '(none)'}\n\n"
            "I will not propose this again unless something has\n"
            "changed. Tell me what is different this time, or\n"
            "ask me for a different approach."
        )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    def update_summary(self) -> None:
        """Rewrite the short, current state of this chat.

        This is what the mind re-reads before every answer.
        """
        lines: List[str] = []

        lines.append(f"# Chat summary")
        lines.append("")
        lines.append(f"Topic: {self.topic or '(unset)'}")
        lines.append(f"Domain: {self.domain}")
        lines.append(f"Created: {time.strftime('%Y-%m-%d %H:%M', time.localtime(self.created_at))}")
        lines.append("")

        if self.verified:
            lines.append("## Verified in this chat")
            for v in self.verified[-20:]:
                lines.append(f"- {v.solution}  ({v.evidence})")
            lines.append("")

        if self.rejected:
            lines.append("## Rejected in this chat (do not repeat)")
            for r in self.rejected[-20:]:
                reason = f"reason: {r.reason}" if r.reason else "no reason recorded"
                lines.append(f"- {r.solution}  ({reason})")
            lines.append("")

        if self.turns:
            lines.append("## Recent turns")
            for t in self.turns[-6:]:
                one = t.text.strip().replace("\n", " ")[:160]
                lines.append(f"- [{t.role}] {one}")
            lines.append("")

        self.summary = "\n".join(lines).strip()
        self._save_summary()

    # --------------------------------------------------------
    # TURNS
    # --------------------------------------------------------

    def add_turn(
        self,
        role: str,
        text: str,
        action: str = "",
        verified: Optional[List[str]] = None,
        rejected: Optional[List[str]] = None,
    ) -> None:
        self.turns.append(
            Turn(
                role=role,
                text=text,
                ts=time.time(),
                action=action,
                verified=verified or [],
                rejected=rejected or [],
            )
        )
        self._save_turns()

    # --------------------------------------------------------
    # PERSISTENCE
    # --------------------------------------------------------

    def save(self) -> None:
        meta = {
            "chat_id": self.chat_id,
            "domain": self.domain,
            "topic": self.topic,
            "topic_lock": self.topic_lock,
            "created_at": self.created_at,
            "pending_clarification": self.pending_clarification,
        }
        self.chat_file.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def load(self) -> None:
        try:
            meta = json.loads(self.chat_file.read_text(encoding="utf-8"))
            # Chat identity is owned by the durable container path supplied
            # by ChatStore. Legacy metadata may contain a stale/mismatched ID
            # and must not override that canonical identity.
            self.domain = meta.get("domain", self.domain)
            self.topic = meta.get("topic", "")
            self.topic_lock = meta.get("topic_lock", self.topic_lock)
            self.created_at = meta.get("created_at", self.created_at)
            pending = meta.get("pending_clarification", {})
            self.pending_clarification = pending if isinstance(pending, dict) else {}
        except Exception:
            pass

        self.turns = self._load_list(self.turns_file, Turn)
        self.verified = self._load_list(self.verified_file, Verified)
        self.rejected = self._load_list(self.rejected_file, Rejected)

        if self.summary_file.exists():
            try:
                self.summary = self.summary_file.read_text(encoding="utf-8")
            except Exception:
                self.summary = ""

    @staticmethod
    def _load_list(path: Path, cls):
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                return []
            return [cls(**item) for item in raw]
        except Exception:
            return []

    def _save_summary(self) -> None:
        self.summary_file.write_text(self.summary, encoding="utf-8")

    def _save_turns(self) -> None:
        self.turns_file.write_text(
            json.dumps([asdict(t) for t in self.turns], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _save_verified(self) -> None:
        self.verified_file.write_text(
            json.dumps([asdict(v) for v in self.verified], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _save_rejected(self) -> None:
        self.rejected_file.write_text(
            json.dumps([asdict(r) for r in self.rejected], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


# ============================================================
# CHAT STORE
# ============================================================

class ChatStore:
    """Manage durable Chat State.

    Authenticated application histories are scoped to an owner. The legacy
    unowned location remains readable through explicit legacy stores only;
    it is never silently assigned to an authenticated account.
    """

    def __init__(self, workspace: Path, owner: Optional[str] = None):
        self.root = Path(workspace) / ".central_mind" / "chats"
        if owner is not None:
            identity = hashlib.sha256(owner.casefold().encode("utf-8")).hexdigest()
            self.root = Path(workspace) / ".central_mind" / "users" / identity / "chats"
        self.root.mkdir(parents=True, exist_ok=True)

    def _chat_path(self, chat_id: str) -> Path:
        if not isinstance(chat_id, str) or not re.fullmatch(r"chat_[A-Za-z0-9_-]+", chat_id):
            raise ValueError("invalid chat identity")
        path = self.root / chat_id
        if path.is_symlink() or path.resolve().parent != self.root.resolve():
            raise ValueError("invalid chat path")
        return path

    def delete(self, chat_id: str) -> bool:
        """Explicit human operation, scoped to this authenticated owner's store."""
        path = self._chat_path(chat_id)
        if not path.is_dir():
            return False
        shutil.rmtree(path)
        return True

    def create(
        self,
        domain: str = "general",
        topic_lock: str = "strict",
    ) -> Chat:
        # A Chat has one canonical identity. The directory name and
        # Chat.chat_id must be identical so ChatStore.load(chat_id)
        # can restore the same durable container later.
        chat_id = Chat._new_id()
        chat_dir = self.root / chat_id

        return Chat(
            root=chat_dir,
            chat_id=chat_id,
            domain=domain,
            topic_lock=topic_lock,
        )

    def load(self, chat_id: str) -> Optional[Chat]:
        try:
            path = self._chat_path(chat_id)
        except ValueError:
            return None
        if not path.exists():
            return None

        # The durable directory name is the canonical Chat identity.
        # Supplying it explicitly keeps legacy chats readable even when
        # older chat.json metadata omitted or disagreed with that identity.
        return Chat(
            root=path,
            chat_id=chat_id,
        )

    def list_ids(self) -> List[str]:
        return sorted(
            [p.name for p in self.root.iterdir() if p.is_dir() and not p.is_symlink() and re.fullmatch(r"chat_[A-Za-z0-9_-]+", p.name)]
        )

    def latest(self) -> Optional[Chat]:
        ids = self.list_ids()
        if not ids:
            return None
        return self.load(ids[-1])
