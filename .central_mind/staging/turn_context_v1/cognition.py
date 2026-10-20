"""Shared Central Mind cognitive contracts.

These structures are deliberately provider/domain independent.

Central Mind owns the cognitive cycle. Models, domains and tools may
contribute information, proposals and results, but they do not own the
decision state represented here.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class TurnContext:
    """Context accompanying one human/application turn.

    This contract carries context, not semantic conclusions and not
    execution authority.

    ``surface`` and ``observations`` describe what the application observed.
    They may help reasoning but are not authoritative domain evidence.

    ``identity`` is reserved for trusted backend-established identity.

    ``conversation`` carries conversation identity and bounded Chat State
    supplied by the trusted runtime. It is not Section 3 permanent Memory.

    ``metadata`` carries generic turn/request metadata.
    """

    surface: Dict[str, Any] = field(default_factory=dict)
    identity: Dict[str, Any] = field(default_factory=dict)
    conversation: Dict[str, Any] = field(default_factory=dict)
    observations: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


OBJECTIVE_OUTCOMES = {"success", "failure", "partial", "unknown"}
VERIFICATION_STATES = {
    "passed",
    "failed",
    "insufficient",
    "not_applicable",
    "not_performed",
}
DISPOSITIONS = {
    "accept",
    "reject",
    "retry",
    "investigate",
    "clarify",
    "request_decision",
}
FAILURE_CODES = {
    "timeout",
    "wrong_output",
    "missing_dependency",
    "import_error",
    "syntax_error",
    "runtime_error",
    "logic_error",
    "context_mismatch",
    "resource_limit",
    "missing_capability",
    "authorization_denied",
    "verification_failed",
    "insufficient_evidence",
    "unknown",
}


@dataclass
class CognitiveStep:
    """One bounded step in a Central Mind plan.

    A step expresses cognitive intent only. It grants no authority.
    Executable component/capability pairs are validated against trusted
    Inventory, while Guard remains authoritative for actual effects.
    """

    step_id: str
    objective: str
    kind: str = "domain"
    component: Optional[str] = None
    capability: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    expected_outcome: str = ""
    confidence: float = 0.0
    rationale: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CognitivePlan:
    objective: str
    recalled_memory: List[Dict[str, Any]] = field(default_factory=list)
    memory_ids: List[str] = field(default_factory=list)

    requirements: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    ambiguities: List[str] = field(default_factory=list)
    missing_information: List[str] = field(default_factory=list)
    clarification_questions: List[Dict[str, Any]] = field(default_factory=list)
    understanding_confidence: float = 0.0

    steps: List[CognitiveStep] = field(default_factory=list)

    strategy: str = "understand_plan_execute_verify_appraise_learn_communicate"
    expected_outcome: str = ""
    max_attempts: int = 1
    should_clarify: bool = False
    rationale: List[str] = field(default_factory=list)

    reasoning_error: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Appraisal:
    objective: str
    objective_outcome: str
    verification_state: str
    disposition: str
    failure_code: Optional[str] = None
    reusable: bool = False
    reusable_reason: str = ""
    capability_gap: Optional[str] = None
    provider: Optional[str] = None
    domain: Optional[str] = None
    memory_ids: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.objective_outcome not in OBJECTIVE_OUTCOMES:
            raise ValueError(
                f"invalid objective outcome: {self.objective_outcome}"
            )
        if self.verification_state not in VERIFICATION_STATES:
            raise ValueError(
                f"invalid verification state: {self.verification_state}"
            )
        if self.disposition not in DISPOSITIONS:
            raise ValueError(f"invalid disposition: {self.disposition}")
        if self.failure_code is not None and self.failure_code not in FAILURE_CODES:
            raise ValueError(f"invalid failure code: {self.failure_code}")

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)
