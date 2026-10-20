"""Temporary bounded reasoning state for Central Mind Reasoner.

This state exists only for one reasoning turn.  It is not permanent Memory,
does not grant authority, and does not itself execute domains, tools or models.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ReasoningEvidence:
    """One trusted or explicitly attributed piece of reasoning evidence."""

    source_kind: str
    source: str
    subject: str
    value: Any
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "source_kind": self.source_kind,
            "source": self.source,
            "subject": self.subject,
            "value": self.value,
            "confidence": max(0.0, min(1.0, float(self.confidence))),
            "metadata": dict(self.metadata),
        }


@dataclass
class ReasoningState:
    """Central Mind-owned working state for one bounded reasoning turn."""

    objective: str
    supplied_context: Dict[str, Any] = field(default_factory=dict)
    recalled_memory: List[Dict[str, Any]] = field(default_factory=list)
    memory_ids: List[str] = field(default_factory=list)

    objective_summary: str = ""
    requirements: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    ambiguities: List[str] = field(default_factory=list)
    missing_information: List[str] = field(default_factory=list)

    evidence: List[ReasoningEvidence] = field(default_factory=list)
    consulted_components: List[str] = field(default_factory=list)
    investigation_results: List[Dict[str, Any]] = field(default_factory=list)

    candidate_steps: List[Dict[str, Any]] = field(default_factory=list)
    rejected_hypotheses: List[str] = field(default_factory=list)
    clarification_questions: List[Dict[str, Any]] = field(default_factory=list)

    understanding_confidence: float = 0.0
    should_clarify: bool = False
    reasoning_error: Optional[str] = None

    cycle_count: int = 0
    consultation_count: int = 0
    no_progress_count: int = 0
    max_cycles: int = 4
    max_consultations: int = 3

    rationale: List[str] = field(default_factory=list)

    def add_evidence(
        self,
        *,
        source_kind: str,
        source: str,
        subject: str,
        value: Any,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.evidence.append(
            ReasoningEvidence(
                source_kind=str(source_kind or "unknown"),
                source=str(source or "unknown"),
                subject=str(subject or ""),
                value=value,
                confidence=confidence,
                metadata=dict(metadata or {}),
            )
        )

    def mark_consulted(self, component: str) -> None:
        name = str(component or "").strip()
        if name and name not in self.consulted_components:
            self.consulted_components.append(name)
        self.consultation_count += 1

    def can_continue(self) -> bool:
        return self.cycle_count < self.max_cycles

    def can_consult(self) -> bool:
        return self.consultation_count < self.max_consultations

    def begin_cycle(self) -> None:
        self.cycle_count += 1

    def evidence_payload(self) -> List[Dict[str, Any]]:
        return [item.as_dict() for item in self.evidence]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "objective": self.objective,
            "supplied_context": dict(self.supplied_context),
            "recalled_memory": list(self.recalled_memory),
            "memory_ids": list(self.memory_ids),
            "objective_summary": self.objective_summary,
            "requirements": list(self.requirements),
            "constraints": list(self.constraints),
            "ambiguities": list(self.ambiguities),
            "missing_information": list(self.missing_information),
            "evidence": self.evidence_payload(),
            "consulted_components": list(self.consulted_components),
            "investigation_results": list(self.investigation_results),
            "candidate_steps": list(self.candidate_steps),
            "rejected_hypotheses": list(self.rejected_hypotheses),
            "clarification_questions": list(self.clarification_questions),
            "understanding_confidence": self.understanding_confidence,
            "should_clarify": self.should_clarify,
            "reasoning_error": self.reasoning_error,
            "cycle_count": self.cycle_count,
            "consultation_count": self.consultation_count,
            "no_progress_count": self.no_progress_count,
            "max_cycles": self.max_cycles,
            "max_consultations": self.max_consultations,
            "rationale": list(self.rationale),
        }
