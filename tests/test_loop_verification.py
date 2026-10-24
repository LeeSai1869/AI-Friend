import sys
import unittest
import json
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CENTRAL_MIND = PROJECT_ROOT / "section_1_central_mind"
sys.path.insert(0, str(CENTRAL_MIND))

from mind.loop import CentralMind
from mind.cognition import CognitivePlan, CognitiveStep
from mind.composer import Composer
from mind.verifier import Verifier
from section_4_chatbox.chatbox import Chatbox
sys.path.insert(0, str(PROJECT_ROOT / "section_5_domains"))
from coding.coding_engine import CodingOrgan


from section_1_central_mind.mind.reasoner import Reasoner
from section_1_central_mind.mind.appraiser import SelfAppraiser
from section_1_central_mind.mind.learner import Learner
from section_1_central_mind.mind.capability_expansion import CapabilityExpansion
from section_1_central_mind.mind.self_assessment.loop import SelfAssessmentLoop

class StubOrgan:
    name = "test-organ"

    def __init__(self, response, verdict):
        self.responses = list(response) if isinstance(response, list) else [response]
        self.verdict = verdict
        self.requests = []

    def handle(self, request):
        self.requests.append(request)
        return self.responses.pop(0)

    def verify(self, response):
        return self.verdict

    def score_event(self, event):
        pass


class StubBoundBroker:
    def __init__(self, component_name):
        self.component_name = component_name


class StubBroker:
    def reset_budget(self):
        pass

    def bind_component(self, info):
        return StubBoundBroker(info.name)

    def bind_central_mind(self):
        return StubBoundBroker("central_mind")


class StubScorer:
    def record(self, *args, **kwargs):
        if not hasattr(self, "records"):
            self.records = []
        self.records.append({"args": args, "kwargs": kwargs})
        return kwargs if kwargs else (args[-1] if args and isinstance(args[-1], dict) else {})


class StubResourceSocket:
    def fulfill(self, requirement, **context):
        if requirement["domain"] == "chat":
            payload = json.loads(context["messages"][-1]["content"])
            return {
                "ok": True,
                "output": "\n".join(payload["verified_evidence"]),
                "model": "test-chat",
            }
        return {
            "ok": True,
            "output": json.dumps({"approved": True, "issues": []}),
            "model": "test-reviewer",
        }


def make_mind(organ):
    organs = organ if isinstance(organ, list) else [organ]
    mind = CentralMind.__new__(CentralMind)
    mind.turn_count = 0
    mind.broker = StubBroker()
    mind.chat_log = []
    mind.chatbox = Chatbox()
    mind.resource_socket = StubResourceSocket()
    mind.caller = object()
    mind.memory = None
    mind.router = SimpleNamespace(
        route=lambda request: [
            SimpleNamespace(
                name=item.name,
                kind="domain",
                entry_module="stub",
                entry_attr="StubOrgan",
                manifest={
                    "memory_domain": (
                        "Cod"
                        if item.name == "coder"
                        else "Gen"
                    ),
                },
            )
            for item in organs
        ]
    )
    mind._load_organ = lambda info: next(
        item for item in organs if item.name == info.name
    )
    mind.verifier = Verifier()
    mind.scorer = StubScorer()
    mind.self_assessment = SelfAssessmentLoop(
        scorer=mind.scorer,
        proposal_queue=None,
        audit_stage=None,
        inventory=None,
    )
    mind.reasoner = Reasoner(memory=None)
    mind.appraiser = SelfAppraiser()
    mind.learner = Learner()
    mind.capability_expansion = CapabilityExpansion()
    mind.composer = Composer()
    mind.questioner = SimpleNamespace(ask=lambda questions: {})
    infos = mind.router.route({})
    from runtime_contract import configure_execution_contract
    configure_execution_contract(mind, infos)
    mind.resource_socket.connect("model", StubResourceSocket().fulfill)
    return mind


class CentralMindVerificationTests(unittest.TestCase):
    def test_central_mind_supplies_recalled_raw_memory_to_assigned_domain(self):
        organ = StubOrgan(
            {"status": "ok", "output": "Analyzed unverified source"},
            {"ok": True, "reason": "analysis supported by evidence"},
        )
        mind = make_mind(organ)
        mind.inventory = SimpleNamespace(
            get=lambda name: SimpleNamespace(
                name=name,
                kind="domain",
                manifest={"memory_domain": "Gen"},
                capabilities=["inspect_code"],
            ) if name == "test-organ" else None,
        )
        raw_entry = {
            "id": "mem_Gen_0000000000001",
            "memory_class": "raw",
            "title": "Trainer source",
            "content": "A user-provided formula that needs checking.",
        }
        plan = CognitivePlan(
            objective="Analyze the formula",
            recalled_memory=[raw_entry],
            memory_ids=[raw_entry["id"]],
            steps=[CognitiveStep(
                step_id="analyze",
                objective="Analyze the formula",
                component="test-organ",
                capability="inspect_code",
            )],
        )

        result = mind.process("Analyze the formula", plan=plan)

        self.assertEqual(result["status"], "ok")
        self.assertIn("Trainer source", organ.requests[0]["text"])
        self.assertIn(
            "A user-provided formula that needs checking.",
            organ.requests[0]["text"],
        )
        self.assertIn("unverified material", organ.requests[0]["text"])

    def test_rejected_answer_is_not_returned_as_success(self):
        organ = StubOrgan(
            {"status": "ok", "output": "REJECTED SECRET ANSWER"},
            {"ok": False, "reason": "verification failed"},
        )
        result = make_mind(organ).process("test request")

        self.assertNotEqual(result.get("status"), "ok")
        self.assertNotIn("REJECTED SECRET ANSWER", str(result))

    def test_accepted_answer_still_works(self):
        organ = StubOrgan(
            {"status": "ok", "output": "Accepted answer"},
            {"ok": True, "reason": "passed"},
        )
        result = make_mind(organ).process("test request")

        self.assertEqual(result.get("status"), "ok")
        self.assertEqual(result.get("output"), "Accepted answer")

    def test_one_rejection_withholds_all_combined_outputs(self):
        accepted = StubOrgan(
            {"status": "ok", "output": "SAFE OTHER ANSWER"},
            {"ok": True, "reason": "passed"},
        )
        accepted.name = "accepted-organ"

        rejected = StubOrgan(
            {"status": "ok", "output": "REJECTED SECRET ANSWER"},
            {"ok": False, "reason": "verification failed"},
        )
        rejected.name = "rejected-organ"

        result = make_mind([accepted, rejected]).process("test request")

        self.assertNotEqual(result.get("status"), "ok")
        self.assertNotIn("SAFE OTHER ANSWER", str(result))
        self.assertNotIn("REJECTED SECRET ANSWER", str(result))

    def test_clarification_flow_is_preserved(self):
        organ = StubOrgan(
            [
                {"status": "needs_answers", "questions": [{"question": "Which one?"}]},
                {"status": "needs_answers", "questions": [{"question": "Please clarify."}]},
            ],
            {"ok": True, "reason": "passed"},
        )
        result = make_mind(organ).process("test request")

        self.assertEqual(result.get("status"), "needs_answers")
        self.assertTrue(result.get("questions"))


class FixedCodingOrgan(CodingOrgan):
    """Use the real CodingOrgan verifier with a controlled test response."""

    def __init__(self, response):
        super().__init__()
        self.test_response = response

    def handle(self, request):
        return self.test_response


class CodingOrganIntegrationTests(unittest.TestCase):
    def test_central_mind_rejects_coding_success_without_evidence(self):
        organ = FixedCodingOrgan({
            "status": "ok",
            "operation": "code_change",
            "output": "UNVERIFIED SECRET: code change succeeded",
            "artifacts": ["example.py"],
        })

        result = make_mind(organ).process("fix example.py")

        self.assertNotEqual(result.get("status"), "ok")
        self.assertNotIn("UNVERIFIED SECRET", str(result))

    def test_central_mind_accepts_coding_success_with_valid_evidence(self):
        organ = FixedCodingOrgan({
            "status": "ok",
            "operation": "code_change",
            "output": "Verified code change",
            "artifacts": ["example.py"],
            "verification": {
                "ok": True,
                "reason": "File write and Python syntax check succeeded",
                "checks": {
                    "file_writes": True,
                    "python_syntax": "passed",
                },
            },
        })

        result = make_mind(organ).process("fix example.py")

        self.assertEqual(result.get("status"), "ok")
        self.assertIn("Verified code change", str(result))


class MemoryDispatchTests(unittest.TestCase):
    def test_organ_receives_client_from_shared_memory_service(self):
        class CapturingOrgan(StubOrgan):
            def handle(self, request):
                self.last_request = request
                return super().handle(request)

        organ = CapturingOrgan(
            {"status": "ok", "output": "Memory dispatch checked"},
            {"ok": True, "reason": "passed"},
        )
        organ.name = "coder"

        client_marker = object()
        client_calls = []

        def make_client(**kwargs):
            client_calls.append(kwargs)
            return client_marker

        mind = make_mind(organ)
        mind.memory_service = SimpleNamespace(client=make_client)

        result = mind.process("test request")

        self.assertEqual(result.get("status"), "ok")
        self.assertIs(organ.last_request["memory"], client_marker)
        self.assertEqual(len(client_calls), 1)
        self.assertEqual(client_calls[0]["actor"], "coder")
        self.assertEqual(client_calls[0]["role"], "domain")
        self.assertEqual(client_calls[0]["domain"], "Cod")


if __name__ == "__main__":
    unittest.main(verbosity=2)
