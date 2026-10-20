import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "section_1_central_mind"))

import pytest
from mind.proposals import (
    ProposalQueue, ProposalContractError,
    KIND_SELF_DIRECTED, KIND_REMOVAL,
)

def _add(q, kind=KIND_SELF_DIRECTED, **ov):
    f = dict(kind=kind, producer="loop_2", objective="x", proposed_action="y",
             evidence={"reason": "r", "observed_signal": "s"},
             scope={}, risk={"level": "low"}, dependents=[],
             affects_central_mind=False)
    f.update(ov)
    return q.append(**f)

def test_roundtrip():
    q = ProposalQueue()
    pid = _add(q)
    p = q.get(pid)
    assert p and p.proposal_id == pid

def test_bad_kind():
    with pytest.raises(ProposalContractError):
        _add(ProposalQueue(), kind="nope")

def test_list_filter():
    q = ProposalQueue()
    pid = _add(q)
    assert len(q.list()) == 1
    q.record_audit(pid, verdict={"verdict": "pass"})
    assert len(q.list(status="audit_passed")) == 1

def test_audit_statuses():
    q = ProposalQueue()
    for v, expect in [("pass", "audit_passed"), ("fail", "audit_failed"),
                      ("needs_more_evidence", "audit_needs_evidence"),
                      ("garbage", "audit_failed")]:
        pid = _add(q)
        q.record_audit(pid, verdict={"verdict": v})
        assert q.get(pid).status == expect

def test_decision_needs_audit():
    q = ProposalQueue()
    pid = _add(q)
    with pytest.raises(ProposalContractError):
        q.record_decision(pid, decision="approve", actor="a", reason="r")

def test_decision_validates():
    q = ProposalQueue()
    pid = _add(q)
    q.record_audit(pid, verdict={"verdict": "pass"})
    with pytest.raises(ProposalContractError):
        q.record_decision(pid, decision="xx", actor="a", reason="r")
    with pytest.raises(ProposalContractError):
        q.record_decision(pid, decision="approve", actor="a", reason="")

def test_decision_records():
    q = ProposalQueue()
    pid = _add(q)
    q.record_audit(pid, verdict={"verdict": "pass"})
    u = q.record_decision(pid, decision="approve", actor="a", reason="ok")
    assert u["status"] == "approved"
    assert u["administrator_decision"]["decision"] == "approve"

def test_no_execution_method():
    forbidden = {"execute", "apply", "run", "pop", "consume", "dispatch"}
    public = {n for n in dir(ProposalQueue) if not n.startswith("_")}
    leaked = public & forbidden
    assert not leaked, f"leaked execution methods: {leaked}"
