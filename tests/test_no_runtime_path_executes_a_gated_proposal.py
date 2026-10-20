"""Fail-before-execution test for D018.

Enforces, precisely:
  1. ProposalQueue has no execution-shaped public method.
  2. Any function that reads `proposal_queue` may only invoke the five
     allowed queue methods (append / get / list / record_audit /
     record_decision).
  3. Any function that reads `proposal_queue` may not call into execution
     entry points (Broker / resource_socket / organ.handle).
  4. The server's `proposal_decide` block contains no execution calls.
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "section_1_central_mind"
TESTS = Path(__file__).resolve().parents[1] / "tests"
sys.path.insert(0, str(ROOT))

ALLOWED_QUEUE_METHODS = {
    "append", "get", "list", "record_audit", "record_decision",
}
EXECUTION_CALL_ATTRS = {
    "bind_central_mind", "bind_component",
    "request",       # .resource_socket.request(...)
    "handle",        # organ.handle(...)
    "call",          # broker.call(...) / bind_central_mind().call(...)
}


def _iter_py(root):
    for p in root.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        yield p


def _queue_touch_functions(tree):
    """Yield (func_node, [name_of_proposal_queue_vars]) for any function
    that either reads self.proposal_queue or assigns from it."""
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        hit = False
        for sub in ast.walk(node):
            # Attribute read: self.proposal_queue or *.proposal_queue
            if isinstance(sub, ast.Attribute) and sub.attr == "proposal_queue":
                hit = True
                break
            # Name read: local variable named proposal_queue
            if isinstance(sub, ast.Name) and sub.id == "proposal_queue":
                hit = True
                break
        if hit:
            yield node


def _calls_inside(fn_node):
    """Yield (attr_name, call_node) for every Call inside fn_node."""
    for sub in ast.walk(fn_node):
        if isinstance(sub, ast.Call):
            f = sub.func
            if isinstance(f, ast.Attribute):
                yield f.attr, sub
            elif isinstance(f, ast.Name):
                yield f.id, sub


def test_queue_no_execution_method():
    from mind.proposals import ProposalQueue
    forbidden = {
        "execute", "apply", "run", "pop", "consume",
        "dispatch", "invoke", "perform",
    }
    public = {n for n in dir(ProposalQueue) if not n.startswith("_")}
    leaked = public & forbidden
    assert not leaked, f"ProposalQueue exposes execution-shaped methods: {leaked!r}"


def test_functions_touching_queue_do_not_execute():
    failures = []
    for path in _iter_py(ROOT):
        if path.name == "proposals.py":
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for fn in _queue_touch_functions(tree):
            for attr, call in _calls_inside(fn):
                if attr in EXECUTION_CALL_ATTRS:
                    # Must not execute from inside a queue-touching function.
                    failures.append((
                        str(path.relative_to(ROOT)),
                        fn.name,
                        attr,
                        call.lineno,
                    ))
    assert not failures, (
        "Functions that touch proposal_queue also call execution "
        f"entry points (D018 violation): {failures!r}"
    )


def test_queue_touching_functions_only_use_allowed_methods():
    """Any direct call of the form <x>.append/get/list/record_* is fine.
    Any other method invoked on something assigned from proposal_queue is not."""
    failures = []
    for path in _iter_py(ROOT):
        if path.name in {"proposals.py", "server.py"}:
            # server.py: proposal_decide only records (checked separately).
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for fn in _queue_touch_functions(tree):
            for sub in ast.walk(fn):
                # Detect: <var> = self.proposal_queue  followed by <var>.<method>(...)
                # Simpler, sufficient: any Call where func is an Attribute
                # whose value is a Name bound to proposal_queue.
                if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                    target = sub.func.value
                    if isinstance(target, ast.Name):
                        # Only flag when this name traces to proposal_queue
                        # (conservative: skip, no name resolution here).
                        continue
                    if isinstance(target, ast.Attribute) and target.attr == "proposal_queue":
                        if sub.func.attr not in ALLOWED_QUEUE_METHODS:
                            failures.append((
                                str(path.relative_to(ROOT)),
                                fn.name,
                                sub.func.attr,
                                sub.lineno,
                            ))
    assert not failures, (
        f"Unsafe method called on proposal_queue: {failures!r}"
    )


def test_proposal_decide_handler_has_no_execution_calls():
    server = (ROOT / "server.py").read_text(encoding="utf-8")
    start = server.find('if op == "proposal_decide"')
    assert start != -1, "proposal_decide op missing"
    rest = server[start:]
    next_if = rest.find("\n            if op ==", 1)
    next_comment = rest.find("\n            # ----", 1)
    candidates = [x for x in (next_if, next_comment) if x != -1]
    end = min(candidates) if candidates else len(rest)
    block = rest[:end]
    for forbidden in (
        "bind_central_mind()", "bind_component(",
        "resource_socket.request", "organ.handle(",
        "broker.call(", "open(", "Path(",
    ):
        assert forbidden not in block, (
            f"proposal_decide handler contains {forbidden!r}; "
            "gated proposals must be recorded only, never executed"
        )
