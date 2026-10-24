import json

from section_1_central_mind.mind.reasoner.head import Reasoner


class _Domain:
    name = "coder"
    kind = "domain"
    manifest = {
        "evidence_capabilities": {
            "project_context": {
                "description": "Report whether a Coding project is open.",
                "read_only": True,
            },
        },
    }
    capabilities = ["inspect_code", "write_code"]


class _Translator:
    name = "languages"
    kind = "domain"
    manifest = {}
    capabilities = ["translate"]


class _Inventory:
    def __init__(self):
        self.domain = _Domain()
        self.translator = _Translator()

    def get(self, name):
        return {
            self.domain.name: self.domain,
            self.translator.name: self.translator,
        }.get(name)

    def all(self):
        return [self.domain, self.translator]

    def capability_catalog(self):
        return [
            {
                "component": domain.name,
                "kind": domain.kind,
                "capability": capability,
                "description": capability.replace("_", " "),
            }
            for domain in self.all()
            for capability in domain.capabilities
        ]

    def validate_capability(self, component, capability):
        domain = self.get(component)
        return domain is not None and capability in domain.capabilities


def _proposal(component="coder", kind="domain"):
    return {
        "objective_summary": "Inspect the active project",
        "requirements": [],
        "constraints": [],
        "ambiguities": [],
        "information_needs": [],
        "consultations": [],
        "candidate_steps": [{
            "step_id": "inspect",
            "objective": "Inspect the active project",
            "kind": kind,
            "component": component if kind == "domain" else None,
            "capability": "inspect_code" if kind == "domain" else None,
            "depends_on": [],
            "requirements": [],
            "constraints": [],
            "expected_outcome": "Return evidence from project files",
            "confidence": 0.95,
            "rationale": ["the objective requires project inspection"],
        }],
        "clarification_candidates": [],
        "understanding_confidence": 0.95,
        "rationale": ["semantic proposal"],
    }


def _reasoner(proposal, **kwargs):
    return Reasoner(
        inventory=_Inventory(),
        semantic_router=lambda **_: json.dumps(proposal),
        **kwargs,
    )


def test_active_window_is_context_not_a_forced_domain_route():
    plan = _reasoner(_proposal(kind="communicate")).plan(
        "Hello, can you help?",
        context={
            "observations": {
                "active_window": {
                    "kind": "specialized",
                    "name": "coding",
                },
            },
        },
    )

    assert plan.reasoning_error is None
    assert [step.kind for step in plan.steps] == ["communicate"]


def test_reasoner_accepts_semantically_selected_domain_without_ui_route():
    plan = _reasoner(_proposal()).plan(
        "Inspect the active project",
        context={
            "observations": {
                "active_window": {"kind": "regular", "surface": "chat"},
            },
        },
    )

    assert plan.reasoning_error is None
    assert [(step.component, step.capability) for step in plan.steps] == [
        ("coder", "inspect_code"),
    ]


def test_evidence_capability_is_catalogued_for_consultation_only():
    reasoner = _reasoner(_proposal())

    evidence_rows = [
        row for row in reasoner._semantic_catalog()
        if row["capability"] == "project_context"
    ]

    assert evidence_rows == [{
        "component": "coder",
        "kind": "domain",
        "capability": "project_context",
        "purpose": "evidence",
        "description": "Report whether a Coding project is open.",
        "metadata": {"description": "Report whether a Coding project is open.", "read_only": True},
    }]


def test_reasoner_prioritizes_central_raw_memory_for_recall():
    calls = []
    raw = {"id": "raw-1", "memory_class": "raw", "content": "trainer source"}
    tested = {"id": "tested-1", "memory_class": "tested", "content": "verified result"}

    class _Memory:
        def recall(self, *, query, memory_class=None, limit):
            calls.append(memory_class)
            if memory_class == "raw":
                return [raw]
            return [tested, raw]

    recalled = Reasoner(memory=_Memory())._recall("source")

    assert calls == ["raw", None]
    assert [item["id"] for item in recalled] == ["raw-1", "tested-1"]


def test_reasoner_surfaces_shared_memory_recall_failure():
    class _BrokenMemory:
        def recall(self, **_):
            raise OSError("memory store unavailable")

    reasoner = Reasoner(
        memory=_BrokenMemory(),
        semantic_router=lambda **_: (_ for _ in ()).throw(
            AssertionError("must not reason without checking memory")
        ),
    )

    plan = reasoner.plan("Use my saved reference")

    assert plan.reasoning_error == (
        "Central Mind memory recall failed: memory store unavailable"
    )


def test_reasoner_can_consult_domain_for_current_project_context():
    calls = []
    proposals = [
        {
            "objective_summary": "Determine if the active project can be read",
            "requirements": [],
            "constraints": [],
            "ambiguities": [],
            "information_needs": [],
            "consultations": [{
                "component": "coder",
                "capability": "project_context",
                "subject": "project status",
                "question": "Is a Coding project open, and what is its top-level structure?",
                "rationale": ["Coding owns its active project context"],
            }],
            "candidate_steps": [{
                "step_id": "check_project_status",
                "objective": "Check project status",
                "kind": "domain",
                "component": "coder",
                "capability": "project_context",
                "depends_on": [],
                "requirements": [],
                "constraints": [],
                "expected_outcome": "Project status",
                "confidence": 0.9,
                "rationale": ["The evidence capability reports project state"],
            }, {
                "step_id": "inspect",
                "objective": "Read relevant project files",
                "kind": "domain",
                "component": "coder",
                "capability": "inspect_code",
                "depends_on": ["check_project_status"],
                "requirements": [],
                "constraints": [],
                "expected_outcome": "Project file evidence",
                "confidence": 0.9,
                "rationale": ["Coding owns project inspection"],
            }],
            "clarification_candidates": [],
            "understanding_confidence": 0.7,
            "rationale": ["project state is discoverable from its owner"],
        },
        {
            "objective_summary": "The active project is open",
            "requirements": [],
            "constraints": [],
            "ambiguities": [],
            "information_needs": [{
                "subject": "Project status",
                "reason": "Confirm the project is available.",
                "material": True,
            }],
            "consultations": [{
                "component": "coder",
                "capability": "project_context",
                "subject": "project status",
                "question": "Is a Coding project open, and what is its top-level structure?",
                "rationale": ["Use the owning domain for project state"],
            }],
            "candidate_steps": [{
                "step_id": "inspect",
                "objective": "Read relevant project files",
                "kind": "domain",
                "component": "coder",
                "capability": "inspect_code",
                "depends_on": [],
                "requirements": [],
                "constraints": [],
                "expected_outcome": "Project file evidence",
                "confidence": 0.9,
                "rationale": ["Coding owns project inspection"],
            }],
            "clarification_candidates": [],
            "understanding_confidence": 0.9,
            "rationale": ["domain evidence confirmed project availability"],
        },
    ]

    def semantic_router(**_):
        return json.dumps(proposals.pop(0))

    class _Socket:
        def request(self, requirement, **context):
            calls.append((requirement.as_dict(), context))
            return {
                "status": "ok",
                "evidence": {
                    "capability": "project_context",
                    "project_open": True,
                    "project": {"name": "sample", "root": "/workspace/sample"},
                    "top_level": [{"name": "src", "type": "dir"}],
                },
            }

    reasoner = Reasoner(
        inventory=_Inventory(),
        semantic_router=semantic_router,
        resource_socket=_Socket(),
        requirement_factory=lambda **kwargs: type(
            "Requirement",
            (),
            {"as_dict": lambda self: dict(kwargs)},
        )(),
    )
    plan = reasoner.plan(
        "Can you read my project files?",
        context={"observations": {"active_window": {"kind": "regular"}}},
    )

    assert len(calls) == 1
    assert calls[0][0] == {
        "kind": "domain",
        "domain": "coder",
        "capability": "project_context",
    }
    assert plan.reasoning_error is None
    assert [(step.component, step.capability) for step in plan.steps] == [
        ("coder", "inspect_code"),
    ]
    assert reasoner.last_evidence[0]["value"]["project_open"] is True


def test_reasoner_falls_back_to_declared_evidence_when_model_omits_consultation():
    calls = []
    proposals = [{
        "objective_summary": "Read Section 1 from the active project",
        "requirements": [],
        "constraints": [],
        "ambiguities": [],
        "information_needs": [{
            "subject": "Active project availability",
            "reason": "The project context must be available before reading files.",
            "material": True,
        }],
        "consultations": [],
        "candidate_steps": [],
        "clarification_candidates": [],
        "understanding_confidence": 0.8,
        "rationale": ["The active project may provide the requested files."],
    }, {
        "objective_summary": "Read Section 1 from the active project",
        "requirements": [],
        "constraints": [],
        "ambiguities": [],
        "information_needs": [],
        "consultations": [],
        "candidate_steps": [{
            "step_id": "inspect",
            "objective": "Read Section 1 from the active project",
            "kind": "domain",
            "component": "coder",
            "capability": "inspect_code",
            "depends_on": [],
            "requirements": [],
            "constraints": [],
            "expected_outcome": "Evidence from Section 1 project files",
            "confidence": 0.9,
            "rationale": ["The project context confirms the project is open."],
        }],
        "clarification_candidates": [],
        "understanding_confidence": 0.9,
        "rationale": ["The project is available for inspection."],
    }]

    def semantic_router(**_):
        return json.dumps(proposals.pop(0))

    class _Socket:
        def request(self, requirement, **context):
            calls.append(requirement.as_dict())
            return {
                "status": "ok",
                "evidence": {
                    "capability": "project_context",
                    "project_open": True,
                    "project": {"name": "AI Friend V1", "root": "/workspace"},
                    "top_level": [{"name": "Section 1", "type": "dir"}],
                },
            }

    reasoner = Reasoner(
        inventory=_Inventory(),
        semantic_router=semantic_router,
        resource_socket=_Socket(),
        requirement_factory=lambda **kwargs: type(
            "Requirement",
            (),
            {"as_dict": lambda self: dict(kwargs)},
        )(),
    )
    plan = reasoner.plan(
        "Can you read Section 1 of my project folder that is open?",
        context={"observations": {"active_window": {"kind": "regular"}}},
    )

    assert calls == [{
        "kind": "domain",
        "domain": "coder",
        "capability": "project_context",
    }]
    assert plan.reasoning_error is None
    assert [(step.component, step.capability) for step in plan.steps] == [
        ("coder", "inspect_code"),
    ]
    assert reasoner.last_evidence[0]["value"]["project_open"] is True


def test_reasoner_asks_for_clarification_when_evidence_route_is_unavailable():
    proposal = {
        "objective_summary": "Read files from the active project",
        "requirements": [],
        "constraints": [],
        "ambiguities": [],
        "information_needs": [{
            "subject": "Active project availability",
            "reason": "Project state is needed before reading files.",
            "material": True,
        }],
        "consultations": [],
        "candidate_steps": [],
        "clarification_candidates": [],
        "understanding_confidence": 0.7,
        "rationale": ["Project state is currently unknown."],
    }

    class _UnavailableSocket:
        def request(self, requirement, **context):
            return {"status": "error", "error": "No active project"}

    reasoner = Reasoner(
        inventory=_Inventory(),
        semantic_router=lambda **_: json.dumps(proposal),
        resource_socket=_UnavailableSocket(),
        requirement_factory=lambda **kwargs: type(
            "Requirement",
            (),
            {"as_dict": lambda self: dict(kwargs)},
        )(),
    )
    plan = reasoner.plan("Read files from the active project")

    assert plan.reasoning_error is None
    assert plan.should_clarify is True
    assert plan.missing_information == ["Active project availability"]
    assert plan.clarification_questions == [{
        "attribute": "Active project availability",
        "question": (
            "I don't have enough trusted information about Active project "
            "availability. Could you clarify it?"
        ),
        "options": [],
        "default": None,
    }]


def test_reasoner_accepts_a_validated_multi_domain_plan():
    proposal = _proposal()
    proposal["candidate_steps"].append({
        "step_id": "translate",
        "objective": "Translate the inspected summary",
        "kind": "domain",
        "component": "languages",
        "capability": "translate",
        "depends_on": ["inspect"],
        "requirements": [],
        "constraints": [],
        "expected_outcome": "Translated summary",
        "confidence": 0.9,
        "rationale": ["the user requested a translation"],
    })
    plan = _reasoner(proposal).plan(
        "Inspect the active project and translate the summary",
        context={"observations": {"active_window": {"kind": "regular"}}},
    )

    assert plan.reasoning_error is None
    assert [step.component for step in plan.steps] == [
        "coder",
        "languages",
    ]
