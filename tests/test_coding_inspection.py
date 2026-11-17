import json
from types import SimpleNamespace

from section_5_domains.coding.inspection import analyzer as analyzer_module
from section_5_domains.coding.inspection import selector as selector_module
from section_5_domains.coding.inspection.analyzer import InspectionAnalyzer
from section_5_domains.coding.inspection.inspector import CodingInspector


def test_inspection_reads_one_followup_batch_when_evidence_has_a_gap(monkeypatch):
    files = ["src/first.py", "src/second.py", "README.md"]
    selector_prompts = []
    analysis_prompts = []
    selector_replies = iter([
        json.dumps({"files": ["src/first.py"], "reason": "initial"}),
        json.dumps({"files": ["src/second.py"], "reason": "follow-up"}),
    ])
    analysis_replies = iter([
        json.dumps({
            "answer": "The entry point is not clear yet.",
            "evidence_sufficient": False,
            "missing_context": "Inspect the second module for its caller.",
        }),
        "The second module is called by the first module.",
    ])

    def select_model(_caller, *, messages, **_kwargs):
        selector_prompts.append(messages[-1]["content"])
        return next(selector_replies)

    def analyze_model(_caller, *, messages, **_kwargs):
        analysis_prompts.append(messages[-1]["content"])
        return next(analysis_replies)

    monkeypatch.setattr(selector_module, "request_model", select_model)
    monkeypatch.setattr(analyzer_module, "request_model", analyze_model)

    class Broker:
        def __init__(self):
            self.paths = []

        def call(self, operation, arguments):
            assert operation == "read_file"
            path = arguments["path"]
            self.paths.append(path)
            return {
                "ok": True,
                "data": {"content": f"contents for {path}"},
            }

    broker = Broker()
    project = SimpleNamespace(
        tree=SimpleNamespace(files=lambda: files),
        memory=SimpleNamespace(read=lambda: {}),
        history=SimpleNamespace(read=lambda: []),
        rules=SimpleNamespace(load=lambda: {}),
        project=SimpleNamespace(to_dict=lambda: {"name": "sample"}),
        require_open=lambda: None,
    )
    result = CodingInspector().inspect(
        task="Explain how the entry point calls its helper.",
        project_context=project,
        broker=broker,
        caller=object(),
    )

    assert result["status"] == "ok"
    assert result["output"].startswith(
        "The second module is called by the first module."
    )
    assert "read 2 file(s) from 3 indexed" in result["output"]
    assert result["inspection"]["files"] == [
        "src/first.py",
        "src/second.py",
    ]
    assert result["inspection"]["coverage"]["additional_batch_read"] is True
    assert broker.paths == ["src/first.py", "src/second.py"]
    assert "Specific evidence gap to address" in selector_prompts[1]
    assert "src/first.py" in selector_prompts[1]
    assert "contents for src/second.py" in analysis_prompts[1]


def test_inspection_reading_obeys_total_context_budget(monkeypatch):
    monkeypatch.setattr(InspectionAnalyzer, "MAX_TOTAL_CHARACTERS", 10)
    analyzer = InspectionAnalyzer()

    class Broker:
        def call(self, _operation, arguments):
            return {"ok": True, "data": {"content": arguments["path"] * 20}}

    inspected = analyzer.read_selected(
        selected_files=["a", "b"],
        broker=Broker(),
    )

    assert inspected == {"a": "aaaaaaaaaa"}
    assert analyzer.last_truncated_files == ["a", "b"]
