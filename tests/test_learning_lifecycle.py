import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "section_8_tools"))

from section_3_memory.api import Memory
from section_3_memory.service import MemoryService


class _Info:
    def __init__(self, name, domain, organ):
        self.name = name
        self.kind = "domain"
        self.manifest = {"memory_domain": domain}
        self.organ = organ


class _Inventory:
    def __init__(self, infos):
        self._infos = infos

    def all(self):
        return list(self._infos)


class _Untestable:
    def evaluate_knowledge(self, proposal):
        return {
            "ok": False,
            "testable": False,
            "reason": "no executable test exists",
            "evidence": {},
        }


class _Passing:
    def evaluate_knowledge(self, proposal):
        return {
            "ok": True,
            "testable": True,
            "reason": "domain test passed",
            "evidence": {"check": "passed"},
        }


class _Failing:
    def evaluate_knowledge(self, proposal):
        return {
            "ok": False,
            "testable": True,
            "reason": "domain test failed",
            "evidence": {"check": "failed"},
        }


class LearningLifecycleTests(unittest.TestCase):
    def setUp(self):
        from section_1_central_mind.mind.loop import CentralMind

        self.CentralMind = CentralMind
        self.temp = TemporaryDirectory()
        self.memory = Memory(root=Path(self.temp.name))
        self.service = MemoryService(self.memory)
        self.client = self.service.client(
            actor="intake",
            role="tool",
            domain="Gen",
        )

    def tearDown(self):
        self.temp.cleanup()

    def make_mind(self, organ):
        mind = object.__new__(self.CentralMind)
        info = _Info("test_domain", "Gen", organ)
        mind.inventory = _Inventory([info])
        mind.memory_service = self.service
        mind._load_organ = lambda candidate: candidate.organ
        self.service.register_proposal_handler(
            mind._receive_memory_proposal
        )
        return mind

    def propose(self):
        return self.client.propose_knowledge(
            title="Lifecycle knowledge",
            content="Knowledge submitted through the canonical proposal path.",
            domain="Gen",
            requested_class="raw",
        )

    def test_submission_stays_pending_after_evaluation(self):
        mind = self.make_mind(_Passing())
        submitted = self.propose()

        self.assertEqual(submitted["status"], "pending")
        self.assertTrue(submitted["learning_evaluation"]["ok"])
        self.assertTrue(submitted["learning_evaluation"]["testable"])
        self.assertEqual(self.memory.count(), 0)

    def test_untestable_system_knowledge_is_rejected_not_raw(self):
        mind = self.make_mind(_Untestable())
        submitted = self.propose()

        result = mind.learn_memory_proposal(submitted["proposal_id"])

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(self.memory.count(), 0)

    def test_passing_domain_evaluation_promotes_to_tested(self):
        mind = self.make_mind(_Passing())
        submitted = self.propose()

        result = mind.learn_memory_proposal(submitted["proposal_id"])

        self.assertEqual(result["status"], "approved")
        self.assertEqual(result["approved_class"], "tested")
        entry = self.memory.get(result["memory_id"])
        self.assertEqual(entry.memory_class, "tested")

    def test_failing_testable_knowledge_is_rejected(self):
        mind = self.make_mind(_Failing())
        submitted = self.propose()

        result = mind.learn_memory_proposal(submitted["proposal_id"])

        self.assertEqual(result["status"], "rejected")
        self.assertIsNone(result["memory_id"])
        self.assertEqual(self.memory.count(), 0)

    def test_no_unique_domain_evaluator_never_promotes_to_tested(self):
        mind = object.__new__(self.CentralMind)
        mind.inventory = _Inventory([])
        mind.memory_service = self.service
        mind._load_organ = lambda candidate: candidate.organ
        self.service.register_proposal_handler(
            mind._receive_memory_proposal
        )

        submitted = self.propose()
        self.assertFalse(submitted["learning_evaluation"]["testable"])

        result = mind.learn_memory_proposal(submitted["proposal_id"])
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(self.memory.count(), 0)


if __name__ == "__main__":
    unittest.main()
