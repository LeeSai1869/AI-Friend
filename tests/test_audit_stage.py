import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "section_1_central_mind"))

from mind.audit import AuditStage
from mind.proposals import ProposalQueue, KIND_SELF_DIRECTED, KIND_REMOVAL

def _make(q, kind, *, risk_level, evidence, affects_central_mind=False):
    pid = q.append(kind=kind, producer="loop_2", objective="x",
                   proposed_action="y", evidence=evidence,
                   risk={"level": risk_level},
                   affects_central_mind=affects_central_mind)
    return q.get(pid)

def test_unknown_kind_fails():
    q = ProposalQueue(); p = _make(q, KIND_SELF_DIRECTED, risk_level="low",
                                    evidence={"reason":"r","observed_signal":"s","dependents_scan":[]})
    p.kind = "x"
    assert AuditStage().evaluate(p)["verdict"] == "fail"

def test_low_risk_passes():
    q = ProposalQueue(); p = _make(q, KIND_SELF_DIRECTED, risk_level="low",
                                    evidence={"reason":"r","observed_signal":"s","dependents_scan":[]})
    assert AuditStage().evaluate(p)["verdict"] == "pass"

def test_high_risk_fails():
    q = ProposalQueue(); p = _make(q, KIND_SELF_DIRECTED, risk_level="high",
                                    evidence={"reason":"r","observed_signal":"s","dependents_scan":[]})
    assert AuditStage().evaluate(p)["verdict"] == "fail"

def test_missing_evidence():
    q = ProposalQueue(); p = _make(q, KIND_SELF_DIRECTED, risk_level="low", evidence={})
    assert AuditStage().evaluate(p)["verdict"] == "needs_more_evidence"

def test_missing_dependents_scan():
    q = ProposalQueue(); p = _make(q, KIND_SELF_DIRECTED, risk_level="low",
                                    evidence={"reason":"r","observed_signal":"s"})
    assert AuditStage().evaluate(p)["verdict"] == "needs_more_evidence"

def test_affects_central_mind_ack():
    q = ProposalQueue()
    p1 = _make(q, KIND_REMOVAL, risk_level="low",
               evidence={"reason":"r","failure_evidence":"f","dependents_scan":[]},
               affects_central_mind=True)
    assert AuditStage().evaluate(p1)["verdict"] == "needs_more_evidence"
    p2 = _make(q, KIND_REMOVAL, risk_level="low",
               evidence={"reason":"r","failure_evidence":"f","dependents_scan":[],
                         "affects_central_mind_acknowledged": True},
               affects_central_mind=True)
    assert AuditStage().evaluate(p2)["verdict"] == "pass"
