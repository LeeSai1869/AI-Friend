"""Configuration for the memory system.

Three memory classes: raw, tested, derived.
Domain prefixes are declared here.
Score formula is declared here.
State is computed from counts - no state tags.
"""
from __future__ import annotations

from pathlib import Path


MEMORY_ROOT = Path(__file__).resolve().parent
ENTRIES_DIR = MEMORY_ROOT / "entries"


DOMAIN_PREFIXES = {
    "Cod":  "coding",
    "Img":  "image",
    "Vid":  "video",
    "Trd":  "trading",
    "Gen":  "general",
    "Mind": "mind",
    "Chr":  "chatbox",
    "Cap":  "capabilities",
}


ID_PREFIX = "mem"
SEQUENCE_DIGITS = 13


VALID_MEMORY_CLASSES = {"raw", "tested", "derived"}


VALID_KINDS = {
    "success", "failure", "fact", "decision", "bug", "fix",
    "observation", "request", "response", "tool_call", "model_call",
    "language", "formula", "pattern", "theory",
}


VALID_STATUSES = {"active", "retired", "superseded"}


VALID_DERIVED_STATUSES = {"active", "contested", "obsolete"}


VALID_ORIGINATOR_TYPES = {
    "model", "trainer", "web", "user", "mind", "tool", "domain",
}


VALID_CROSS_REF_REASONS = {
    "used_by", "context", "contradicts", "extends",
    "duplicates", "depends_on", "derived_from",
}


VALID_FAILURE_CODES = {
    "timeout", "wrong_output", "missing_dependency", "import_error",
    "syntax_error", "runtime_error", "logic_error", "context_mismatch",
    "resource_limit", "unknown",
}


FAILURE_WEIGHT = 2.0
SMOOTHING = 1.0


VERIFIED_THRESHOLD = 3


def compute_score(success_count: int, failure_count: int) -> float:
    num = success_count - FAILURE_WEIGHT * failure_count
    den = success_count + failure_count + SMOOTHING
    return num / den


def compute_state(success_count: int, failure_count: int) -> str:
    """The state of an entry, computed from its counts.

    Never stored as a tag. Always computed on read.
    """
    if success_count == 0 and failure_count == 0:
        return "untested"
    if success_count == 0 and failure_count > 0:
        return "rejected"
    if success_count > 0 and failure_count == 0:
        if success_count >= VERIFIED_THRESHOLD:
            return "verified"
        return "provisional"
    return "unstable"
