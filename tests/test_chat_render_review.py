import json
from types import SimpleNamespace

from section_1_central_mind.mind.loop import CentralMind
from section_4_chatbox.chatbox import Chatbox


class _Socket:
    def __init__(self, review):
        self.review = review
        self.requests = []

    def request(self, requirement, **kwargs):
        self.requests.append((requirement, kwargs))
        if requirement.domain == "chat":
            payload = json.loads(kwargs["messages"][-1]["content"])
            if any(
                item.get("source") == "reasoner"
                and item.get("value", {}).get("status") == "incomplete"
                for item in payload.get("verified_evidence", [])
                if isinstance(item, dict)
            ):
                output = (
                    "I couldn't verify whether the project files are "
                    "accessible. Please select or open the project, then "
                    "ask me again."
                )
            else:
                output = "The project files are readable."
            return {
                "ok": True,
                "output": output,
                "model": "chat-renderer",
            }
        return {
            "ok": True,
            "output": self.review,
            "model": "mind-reviewer",
        }


def _mind(review):
    mind = CentralMind.__new__(CentralMind)
    mind.chatbox = Chatbox()
    mind.resource_socket = _Socket(review)
    return mind


def _plan():
    return SimpleNamespace(
        objective="Can you read my project files?",
        as_dict=lambda: {"objective": "Can you read my project files?"},
    )


def _step():
    return SimpleNamespace(
        kind="communicate",
        as_dict=lambda: {"kind": "communicate"},
    )


def test_chat_draft_returns_only_after_central_mind_approves():
    mind = _mind('{"approved": true, "issues": []}')

    result = mind._communicate(
        _plan(),
        _step(),
        ["Coding reports the open project contains src/."],
        [],
    )

    assert result["status"] == "ok"
    assert result["output"] == "The project files are readable."
    assert result["cognition"]["communication_review"]["reviewed_by"] == "central_mind"
    assert [
        (requirement.domain, requirement.capability)
        for requirement, _ in mind.resource_socket.requests
    ] == [("chat", "answer"), ("general", "reason")]


def test_central_mind_withholds_unapproved_chat_draft():
    mind = _mind('{"approved": false, "issues": ["Claim is unsupported"]}')

    result = mind._communicate(
        _plan(),
        _step(),
        [],
        [],
    )

    assert result["status"] == "error"
    assert "The project files are readable." not in str(result)
    assert result["cognition"]["communication_review"]["ok"] is False


def test_central_mind_rejects_malformed_audit_result():
    mind = _mind("not JSON")

    result = mind._communicate(_plan(), _step(), [], [])

    assert result["status"] == "error"
    assert "invalid JSON" in result["error"]


def test_process_passes_reasoning_consultation_evidence_to_chat():
    evidence = {
        "source_kind": "domain",
        "source": "coder",
        "subject": "project status",
        "value": {"project_open": True, "project": {"name": "AI Friend V1"}},
        "confidence": 1.0,
        "metadata": {
            "capability": "project_context",
            "read_only_consultation": True,
        },
    }
    mind = _mind('{"approved": true, "issues": []}')
    plan = SimpleNamespace(
        objective="Can you read project files?",
        steps=[_step()],
        should_clarify=False,
        reasoning_error=None,
        as_dict=lambda: {"objective": "Can you read project files?"},
    )
    mind.turn_count = 0
    mind.chat_log = []
    mind.reasoner = SimpleNamespace(
        plan=lambda *_args, **_kwargs: plan,
        last_evidence=[evidence],
    )

    result = mind.process("Can you read project files?")

    assert result["status"] == "ok"
    chat_request = mind.resource_socket.requests[0][1]["messages"]
    render_payload = json.loads(chat_request[-1]["content"])
    assert render_payload["verified_evidence"] == [evidence]


def test_reasoning_failure_is_rendered_by_chat_and_keeps_error_status():
    mind = _mind('{"approved": true, "issues": []}')
    plan = SimpleNamespace(
        objective="Can you read project files?",
        steps=[],
        should_clarify=False,
        reasoning_error=(
            "material information remains unresolved, but no trusted "
            "investigation or human clarification route was established"
        ),
        as_dict=lambda: {"objective": "Can you read project files?"},
    )
    mind.turn_count = 0
    mind.chat_log = []
    mind.reasoner = SimpleNamespace(
        plan=lambda *_args, **_kwargs: plan,
        last_evidence=[],
    )

    result = mind.process("Can you read project files?")

    assert result["status"] == "error"
    assert result["error"] == plan.reasoning_error
    assert "couldn't verify" in result["output"]
    render_payload = json.loads(
        mind.resource_socket.requests[0][1]["messages"][-1]["content"]
    )
    assert render_payload["verified_evidence"][0]["value"] == {
        "status": "incomplete",
        "reason": plan.reasoning_error,
    }
