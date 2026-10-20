import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CENTRAL_MIND = PROJECT_ROOT / "section_1_central_mind"

sys.path.insert(0, str(CENTRAL_MIND))

from mind.loop import CentralMind
from mind.composer import Composer
from mind.verifier import Verifier


from section_1_central_mind.mind.reasoner import Reasoner
from section_1_central_mind.mind.appraiser import SelfAppraiser
from section_1_central_mind.mind.learner import Learner
from section_1_central_mind.mind.capability_expansion import CapabilityExpansion

class BoundMarker:
    def __init__(self, chain):
        self.chain = tuple(chain)


class RecordingBroker:
    def __init__(self):
        self.bound_components = []
        self.central_bind_count = 0

    def reset_budget(self):
        pass

    def bind_component(self, info):
        self.bound_components.append(info)
        return BoundMarker(("central_mind", info.name))

    def bind_central_mind(self):
        self.central_bind_count += 1
        return BoundMarker(("central_mind",))


class CapturingOrgan:
    def __init__(self, name):
        self.name = name
        self.requests = []

    def handle(self, request):
        self.requests.append(request)
        return {
            "status": "ok",
            "output": f"{self.name} handled",
        }

    def verify(self, response):
        return {
            "ok": True,
            "reason": "passed",
        }


class StubScorer:
    def record(self, *args, **kwargs):
        if not hasattr(self, "records"):
            self.records = []
        self.records.append({"args": args, "kwargs": kwargs})
        return kwargs if kwargs else (args[-1] if args and isinstance(args[-1], dict) else {})


def make_mind(organs):
    mind = CentralMind.__new__(CentralMind)
    mind.turn_count = 0
    mind.broker = RecordingBroker()
    mind.chat_log = []
    mind.caller = object()
    mind.memory = None
    mind.memory_service = None

    infos = [
        SimpleNamespace(
            name=organ.name,
            kind="domain",
            entry_module="stub",
            entry_attr="CapturingOrgan",
            manifest={},
        )
        for organ in organs
    ]

    by_name = {
        organ.name: organ
        for organ in organs
    }

    mind.router = SimpleNamespace(
        route=lambda request: infos,
    )

    mind._load_organ = lambda info: by_name[info.name]
    mind.verifier = Verifier()
    mind.scorer = StubScorer()
    mind.reasoner = Reasoner(memory=None)
    mind.appraiser = SelfAppraiser()
    mind.learner = Learner()
    mind.capability_expansion = CapabilityExpansion()
    mind.composer = Composer()
    mind.questioner = SimpleNamespace(
        ask=lambda questions: {},
    )

    return mind, infos


class CentralMindRuntimeDelegationTests(unittest.TestCase):

    def test_each_routed_domain_receives_its_own_bound_broker(self):
        coder = CapturingOrgan("coder")
        trading = CapturingOrgan("trading")

        mind, infos = make_mind([coder, trading])

        result = mind.process("test")

        self.assertEqual(result.get("status"), "ok")

        self.assertEqual(
            mind.broker.bound_components,
            infos,
        )

        self.assertEqual(
            coder.requests[0]["broker"].chain,
            ("central_mind", "coder"),
        )

        self.assertEqual(
            trading.requests[0]["broker"].chain,
            ("central_mind", "trading"),
        )

    def test_master_broker_is_never_given_to_domain(self):
        coder = CapturingOrgan("coder")

        mind, _ = make_mind([coder])
        mind.process("test")

        received = coder.requests[0]["broker"]

        self.assertIsNot(received, mind.broker)
        self.assertNotIn(
            "broker",
            {
                "text": "test",
                "caller": mind.caller,
                "memory": mind.memory,
            },
        )

    def test_clarification_reuses_same_bound_domain_view(self):
        class ClarifyingOrgan(CapturingOrgan):
            def handle(self, request):
                self.requests.append(request)

                if len(self.requests) == 1:
                    return {
                        "status": "needs_answers",
                        "questions": [
                            {"question": "Which one?"}
                        ],
                    }

                return {
                    "status": "ok",
                    "output": "done",
                }

        organ = ClarifyingOrgan("coder")
        mind, _ = make_mind([organ])

        mind.questioner = SimpleNamespace(
            ask=lambda questions: {
                "answer": "one",
            },
        )

        result = mind.process("test")

        self.assertEqual(result.get("status"), "ok")
        self.assertEqual(len(organ.requests), 2)

        first = organ.requests[0]["broker"]
        second = organ.requests[1]["broker"]

        self.assertIs(first, second)
        self.assertEqual(
            first.chain,
            ("central_mind", "coder"),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
