#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/jhanzeebakbar/Desktop/AI Friend V1"
cd "$ROOT"

echo "== Increment 0: install, test, verify, remove stale =="
echo "Project root: $ROOT"
echo

# ---- 1. New modules ---------------------------------------------------
echo "[1/8] Writing mind/proposals.py"
cat > section_1_central_mind/mind/proposals.py <<'PY'
"""Gated proposal queue for Central Mind."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


KIND_SELF_DIRECTED = "self_directed"
KIND_REMOVAL = "removal"
VALID_KINDS = frozenset({KIND_SELF_DIRECTED, KIND_REMOVAL})

VALID_STATUSES = frozenset({
    "proposed", "under_audit", "audit_passed", "audit_failed",
    "audit_needs_evidence", "approved", "rejected", "deferred", "expired",
})

VALID_DECISIONS = frozenset({"approve", "reject", "defer"})


class ProposalContractError(ValueError):
    pass


@dataclass
class Proposal:
    proposal_id: str
    kind: str
    producer: str
    objective: str
    proposed_action: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    scope: Dict[str, Any] = field(default_factory=dict)
    risk: Dict[str, Any] = field(default_factory=dict)
    dependents: List[str] = field(default_factory=list)
    affects_central_mind: bool = False
    status: str = "proposed"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    audit_verdict: Optional[Dict[str, Any]] = None
    administrator_decision: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        if not self.proposal_id or not isinstance(self.proposal_id, str):
            raise ProposalContractError("proposal_id required")
        if self.kind not in VALID_KINDS:
            raise ProposalContractError(f"unknown kind: {self.kind!r}")
        if self.status not in VALID_STATUSES:
            raise ProposalContractError(f"unknown status: {self.status!r}")
        if not self.producer: raise ProposalContractError("producer required")
        if not self.objective: raise ProposalContractError("objective required")
        if not self.proposed_action: raise ProposalContractError("proposed_action required")

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProposalQueue:
    MAX_PROPOSALS = 1000

    def __init__(self, max_proposals: int = MAX_PROPOSALS):
        self._max = max(1, int(max_proposals))
        self._items: Dict[str, Proposal] = {}
        self._order: List[str] = []

    def append(self, *, kind, producer, objective, proposed_action,
               evidence=None, scope=None, risk=None, dependents=None,
               affects_central_mind=False) -> str:
        pid = "prop_" + uuid.uuid4().hex
        p = Proposal(
            proposal_id=pid, kind=kind, producer=producer,
            objective=objective, proposed_action=proposed_action,
            evidence=dict(evidence or {}), scope=dict(scope or {}),
            risk=dict(risk or {}), dependents=list(dependents or []),
            affects_central_mind=bool(affects_central_mind),
        )
        self._items[pid] = p
        self._order.append(pid)
        while len(self._order) > self._max:
            self._items.pop(self._order.pop(0), None)
        return pid

    def get(self, pid: str) -> Optional[Proposal]:
        return self._items.get(str(pid or ""))

    def list(self, *, status: Optional[str] = None) -> List[Dict[str, Any]]:
        out = []
        for pid in self._order:
            p = self._items.get(pid)
            if p is None: continue
            if status is not None and p.status != status: continue
            out.append(p.as_dict())
        return out

    def record_audit(self, pid: str, *, verdict: Dict[str, Any]) -> Dict[str, Any]:
        p = self._require(pid)
        p.audit_verdict = dict(verdict)
        v = str(verdict.get("verdict") or "").strip()
        p.status = ("audit_passed" if v == "pass"
                    else "audit_needs_evidence" if v == "needs_more_evidence"
                    else "audit_failed")
        p.updated_at = time.time()
        return p.as_dict()

    def record_decision(self, pid: str, *, decision, actor, reason) -> Dict[str, Any]:
        p = self._require(pid)
        if decision not in VALID_DECISIONS:
            raise ProposalContractError(f"unknown decision: {decision!r}")
        if not reason or not reason.strip():
            raise ProposalContractError("reason required")
        if not actor or not actor.strip():
            raise ProposalContractError("actor required")
        if p.status != "audit_passed":
            raise ProposalContractError(f"status {p.status!r} rejects decision")
        p.administrator_decision = {
            "decision": decision, "actor": actor, "reason": reason,
            "decided_at": time.time(),
        }
        p.status = {"approve": "approved", "reject": "rejected", "defer": "deferred"}[decision]
        p.updated_at = time.time()
        return p.as_dict()

    def _require(self, pid: str) -> Proposal:
        p = self.get(pid)
        if p is None:
            raise ProposalContractError(f"unknown proposal_id: {pid!r}")
        return p
PY

echo "[2/8] Writing mind/audit.py"
cat > section_1_central_mind/mind/audit.py <<'PY'
"""Deterministic audit stage for gated proposals."""
from __future__ import annotations
from typing import Any, Dict, List


DEFAULT_POLICY = {
    "self_directed": {
        "allowed_risk_levels": {"low", "medium"},
        "required_evidence_keys": {"reason", "observed_signal"},
        "dependents_scan_required": True,
        "affects_central_mind_acknowledgement_required": True,
    },
    "removal": {
        "allowed_risk_levels": {"low", "medium", "high"},
        "required_evidence_keys": {"reason", "failure_evidence"},
        "dependents_scan_required": True,
        "affects_central_mind_acknowledgement_required": True,
    },
}


class AuditStage:
    def __init__(self, policy=None):
        self.policy = dict(policy) if isinstance(policy, dict) else dict(DEFAULT_POLICY)

    def evaluate(self, proposal) -> Dict[str, Any]:
        kind = getattr(proposal, "kind", None)
        policy = self.policy.get(kind)
        if policy is None:
            return self._v("fail", f"no audit policy for {kind!r}", [])
        checked = []
        risk = str((getattr(proposal, "risk", {}) or {}).get("level", "")).lower()
        if risk not in policy["allowed_risk_levels"]:
            return self._v("fail", f"risk {risk!r} not allowed", ["risk_level"])
        checked.append("risk_level")
        ev = dict(getattr(proposal, "evidence", {}) or {})
        missing = [k for k in policy["required_evidence_keys"]
                   if k not in ev or not ev.get(k)]
        if missing:
            return self._v("needs_more_evidence",
                           f"missing: {sorted(missing)!r}", checked + ["required_evidence"])
        checked.append("required_evidence")
        if policy["dependents_scan_required"] and "dependents_scan" not in ev:
            return self._v("needs_more_evidence", "dependents_scan required",
                           checked + ["dependents_scan"])
        checked.append("dependents_scan")
        if (policy["affects_central_mind_acknowledgement_required"]
                and bool(getattr(proposal, "affects_central_mind", False))):
            if ev.get("affects_central_mind_acknowledged") is not True:
                return self._v("needs_more_evidence",
                               "affects_central_mind_acknowledged required",
                               checked + ["affects_central_mind_acknowledgement"])
            checked.append("affects_central_mind_acknowledgement")
        return self._v("pass", "all checks passed", checked)

    @staticmethod
    def _v(verdict, reason, checked):
        return {"verdict": verdict, "reason": reason, "checked": list(checked)}
PY

echo "[3/8] Writing mind/scheduler.py"
cat > section_1_central_mind/mind/scheduler.py <<'PY'
"""Generic, process-scoped scheduler."""
from __future__ import annotations
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class _Job:
    name: str
    fn: Callable[[], Any]
    interval_seconds: float
    next_run_at: float
    consecutive_failures: int = 0
    skip_intervals: int = 0
    last_error: Optional[str] = None
    runs: int = 0


class Scheduler:
    MAX_BACKOFF_SKIPS = 4

    def __init__(self, *, logger: Optional[Callable[[str], None]] = None):
        self._logger = logger or (lambda m: None)
        self._jobs: Dict[str, _Job] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def register(self, name, fn, *, interval_seconds):
        if not callable(fn): raise TypeError("fn must be callable")
        if interval_seconds <= 0: raise ValueError("interval must be > 0")
        key = str(name or "").strip()
        if not key: raise ValueError("name required")
        with self._lock:
            self._jobs[key] = _Job(
                name=key, fn=fn,
                interval_seconds=float(interval_seconds),
                next_run_at=time.time() + float(interval_seconds),
            )

    def unregister(self, name):
        with self._lock:
            self._jobs.pop(str(name or "").strip(), None)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self, *, timeout=5.0):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    def run_once(self, name):
        with self._lock:
            job = self._jobs.get(str(name or "").strip())
        if job is None:
            return None
        return self._execute(job)

    def status(self):
        with self._lock:
            return [
                {"name": j.name, "interval_seconds": j.interval_seconds,
                 "next_run_at": j.next_run_at,
                 "consecutive_failures": j.consecutive_failures,
                 "skip_intervals": j.skip_intervals,
                 "runs": j.runs, "last_error": j.last_error}
                for j in self._jobs.values()
            ]

    def _run(self):
        while not self._stop.is_set():
            now = time.time()
            with self._lock:
                jobs = list(self._jobs.values())
            for job in jobs:
                if self._stop.is_set():
                    return
                if job.next_run_at > now:
                    continue
                self._execute(job)
            time.sleep(0.5)

    def _execute(self, job):
        job.runs += 1
        try:
            job.fn()
            job.consecutive_failures = 0
            job.skip_intervals = 0
            job.last_error = None
            ok, error = True, None
        except Exception as exc:
            job.consecutive_failures += 1
            job.last_error = str(exc)
            job.skip_intervals = min(
                self.MAX_BACKOFF_SKIPS,
                max(job.skip_intervals, job.consecutive_failures - 1))
            ok, error = False, str(exc)
            self._logger(f"[scheduler] {job.name} failed: {exc}")
        job.next_run_at = time.time() + job.interval_seconds * (1 + job.skip_intervals)
        return {"job": job.name, "ok": ok, "error": error,
                "next_run_at": job.next_run_at,
                "consecutive_failures": job.consecutive_failures,
                "skip_intervals": job.skip_intervals}
PY

# ---- 2. Patch mind/__init__.py ----------------------------------------
echo "[4/8] Patching mind/__init__.py"
cat > section_1_central_mind/mind/__init__.py <<'PY'
from .loop import CentralMind
from .organ import Organ
from .proposals import Proposal, ProposalQueue
from .audit import AuditStage
from .scheduler import Scheduler

__all__ = [
    "CentralMind", "Organ", "Proposal", "ProposalQueue",
    "AuditStage", "Scheduler",
]
PY

# ---- 3. Patch loop.py (one import + one line) -------------------------
echo "[5/8] Patching loop.py"
python3 - <<'PYEOF'
path = "section_1_central_mind/mind/loop.py"
src = open(path, encoding="utf-8").read()
if "from .proposals import ProposalQueue" not in src:
    anchor = "        from .caller import Caller\n"
    assert anchor in src, "caller import anchor missing"
    src = src.replace(anchor, anchor + "        from .proposals import ProposalQueue\n", 1)
if "self.proposal_queue = ProposalQueue()" not in src:
    anchor2 = "        self.caller = Caller(self.inventory, self._load_organ, self.model_router)\n"
    assert anchor2 in src, "caller instantiation anchor missing"
    src = src.replace(anchor2, anchor2 + "        self.proposal_queue = ProposalQueue()\n", 1)
open(path, "w", encoding="utf-8").write(src)
print("  patched loop.py")
PYEOF

# ---- 4. Patch config.py -----------------------------------------------
echo "[6/8] Patching config.py"
python3 - <<'PYEOF'
path = "section_1_central_mind/config.py"
src = open(path, encoding="utf-8").read()
if '"evolution_interval": 20,' in src:
    src = src.replace('    "evolution_interval": 20,\n', '', 1)
    open(path, "w", encoding="utf-8").write(src)
    print("  removed evolution_interval")
else:
    print("  already absent")
PYEOF

# ---- 5. Patch auth_service.py docstring -------------------------------
echo "[7/8] Patching auth_service.py docstring"
python3 - <<'PYEOF'
path = "section_1_central_mind/auth_service.py"
src = open(path, encoding="utf-8").read()
old = '''"""Isolated authentication service for AI Friend V1.

This module is not yet connected to the WebSocket server.
Use a private, user-owned directory for its database.
"""'''
new = '''"""Authentication service for AI Friend V1.

Wired into the WebSocket server (see server.py). Sessions are validated
on every protected request. Use a private, user-owned directory for its
database.
"""'''
if old in src:
    src = src.replace(old, new, 1)
    open(path, "w", encoding="utf-8").write(src)
    print("  docstring updated")
else:
    print("  docstring already updated or different — skipping")
PYEOF

# ---- 6. Patch server.py (remove tool_loop import + add two ops) -------
echo "[8/8] Patching server.py"
python3 - <<'PYEOF'
path = "section_1_central_mind/server.py"
src = open(path, encoding="utf-8").read()

# 6a. remove dead import
if "from mind.tool_loop import ToolLoop\n" in src:
    src = src.replace("from mind.tool_loop import ToolLoop\n", "", 1)
    print("  removed tool_loop import")

# 6b. add proposal ops if absent
if 'if op == "proposal_list":' not in src:
    anchor = '            # ---- inventory ------------------------------------------------\n            if op == "inventory":'
    assert anchor in src, "inventory anchor missing"
    insert = '''            # ---- gated proposals: list (read-only) ------------------------
            #
            # D018 / D019: gated proposals are NEVER executed by the runtime.
            # proposal_list is read-only. proposal_decide records only.
            # Execution is exclusively an Administrator action, performed
            # OUTSIDE the runtime.
            if op == "proposal_list":
                if account is None or account.get("role") != "administrator":
                    await websocket.send(json.dumps({
                        "op": "proposal_list_result", "ok": False,
                        "error": "administrator role required",
                    }))
                    continue
                q = getattr(mind, "proposal_queue", None)
                rows = q.list(status=data.get("status")) if q is not None else []
                await websocket.send(json.dumps({
                    "op": "proposal_list_result", "ok": True, "proposals": rows,
                }))
                continue

            if op == "proposal_decide":
                if account is None or account.get("role") != "administrator":
                    await websocket.send(json.dumps({
                        "op": "proposal_decide_result", "ok": False,
                        "error": "administrator role required",
                    }))
                    continue
                pid = str(data.get("proposal_id") or "").strip()
                dec = str(data.get("decision") or "").strip().lower()
                why = str(data.get("reason") or "").strip()
                if not pid or not dec or not why:
                    await websocket.send(json.dumps({
                        "op": "proposal_decide_result", "ok": False,
                        "error": "proposal_id, decision, reason required",
                    }))
                    continue
                q = getattr(mind, "proposal_queue", None)
                if q is None:
                    await websocket.send(json.dumps({
                        "op": "proposal_decide_result", "ok": False,
                        "error": "queue unavailable",
                    }))
                    continue
                try:
                    updated = q.record_decision(
                        pid, decision=dec,
                        actor=str(account.get("username") or "admin"),
                        reason=why)
                except Exception as exc:
                    await websocket.send(json.dumps({
                        "op": "proposal_decide_result", "ok": False,
                        "error": str(exc),
                    }))
                    continue
                try:
                    auth_service._audit_committed(
                        "proposal_decision_recorded",
                        actor=str(account.get("username") or "admin"),
                        subject=pid,
                        detail={"decision": dec, "reason": why})
                except Exception:
                    pass
                await websocket.send(json.dumps({
                    "op": "proposal_decide_result", "ok": True, "proposal": updated,
                }))
                continue

'''
    src = src.replace(anchor, insert + anchor, 1)
    print("  inserted proposal_list and proposal_decide")
open(path, "w", encoding="utf-8").write(src)
PYEOF

# ---- 7. Remove stale tool_loop.py -------------------------------------
echo "[cleanup] Removing mind/tool_loop.py"
if [ -f section_1_central_mind/mind/tool_loop.py ]; then
  rm section_1_central_mind/mind/tool_loop.py
  echo "  deleted"
else
  echo "  already absent"
fi

# ---- 8. Write tests ---------------------------------------------------
mkdir -p tests

cat > tests/test_proposals_queue.py <<'PY'
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
PY

cat > tests/test_audit_stage.py <<'PY'
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
PY

cat > tests/test_scheduler.py <<'PY'
import time
from mind.scheduler import Scheduler

def test_start_stop():
    calls = []
    s = Scheduler()
    s.register("j", lambda: calls.append(1), interval_seconds=0.05)
    s.start(); time.sleep(0.2); s.stop()
    assert len(calls) >= 1

def test_job_exception_isolated():
    def boom(): raise RuntimeError("boom")
    s = Scheduler()
    s.register("j", boom, interval_seconds=0.05)
    s.start(); time.sleep(0.15); s.stop()
    status = {r["name"]: r for r in s.status()}
    assert status["j"]["consecutive_failures"] >= 1

def test_run_once():
    s = Scheduler()
    s.register("j", lambda: None, interval_seconds=60)
    r = s.run_once("j")
    assert r["ok"] is True

def test_register_validates():
    s = Scheduler()
    try: s.register("", lambda: None, interval_seconds=1); assert False
    except ValueError: pass
    try: s.register("j", "x", interval_seconds=1); assert False
    except TypeError: pass
    try: s.register("j", lambda: None, interval_seconds=0); assert False
    except ValueError: pass

def test_add_after_start():
    s = Scheduler(); a=[]; b=[]
    s.register("a", lambda: a.append(1), interval_seconds=0.05)
    s.start(); time.sleep(0.1)
    s.register("b", lambda: b.append(1), interval_seconds=0.05)
    time.sleep(0.2); s.stop()
    assert len(a) >= 1 and len(b) >= 1
PY

cat > tests/test_no_runtime_path_executes_a_gated_proposal.py <<'PY'
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "section_1_central_mind"

def _sources():
    for p in ROOT.rglob("*.py"):
        if "__pycache__" in p.parts or p.name == "proposals.py":
            continue
        yield p

def test_queue_no_execution_method():
    from mind.proposals import ProposalQueue
    forbidden = {"execute","apply","run","pop","consume","dispatch","invoke","perform"}
    public = {n for n in dir(ProposalQueue) if not n.startswith("_")}
    assert not (public & forbidden)

def test_no_module_consumes_gated_proposal():
    imports = ("from mind.proposals import","from .proposals import",
               ".proposal_queue.",".proposal_queue =")
    calls = ("bind_central_mind().call","bind_component(",
             ".resource_socket.request","organ.handle(","broker.call(")
    bad = []
    for p in _sources():
        t = p.read_text(encoding="utf-8", errors="replace")
        if any(s in t for s in imports) and any(s in t for s in calls):
            if p.name == "server.py":
                continue
            bad.append(str(p))
    assert not bad, bad

def test_decide_handler_no_execution():
    t = (ROOT / "server.py").read_text(encoding="utf-8")
    start = t.find('if op == "proposal_decide"')
    assert start != -1
    rest = t[start:]
    a = rest.find("\n            if op ==", 1)
    b = rest.find("\n            # ----", 1)
    cands = [x for x in (a,b) if x != -1]
    block = rest[:min(cands)] if cands else rest
    for f in ("bind_central_mind()","bind_component(","resource_socket.request",
              "organ.handle(","broker.call(","open(","Path("):
        assert f not in block, f"{f} in proposal_decide"
PY

cat > tests/test_caller_kept.py <<'PY'
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent / "section_1_central_mind"

def test_importable():
    from mind.caller import Caller  # noqa
    from mind.router import Router  # noqa

def test_loop_instantiates():
    t = (ROOT / "mind" / "loop.py").read_text(encoding="utf-8")
    assert "Caller(" in t
PY

cat > tests/test_tool_loop_removed.py <<'PY'
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent / "section_1_central_mind"

def test_module_absent():
    assert not (ROOT / "mind" / "tool_loop.py").exists()

def test_no_imports():
    for p in ROOT.rglob("*.py"):
        if "__pycache__" in p.parts: continue
        assert "tool_loop" not in p.read_text(encoding="utf-8", errors="replace"), str(p)
PY

echo
echo "== Increment 0 installed =="
echo
echo "Run:"
echo "  cd \"$ROOT\""
echo "  pip3 install pytest"
echo "  python3 -m pytest tests/test_proposals_queue.py tests/test_audit_stage.py tests/test_scheduler.py tests/test_no_runtime_path_executes_a_gated_proposal.py tests/test_caller_kept.py tests/test_tool_loop_removed.py -v"
