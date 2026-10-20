import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "section_8_tools"))

from section_3_memory.api import Memory
from section_3_memory.service import MemoryService
from section_8_tools.intake.intake import IntakeCommit


class IntakeMemoryServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.memory = Memory(root=self.root / "memory")
        self.service = MemoryService(self.memory)
        self.intake_client = self.service.client(
            actor="intake",
            role="tool",
            domain="Gen",
        )
        self.tool = IntakeCommit(self.root, broker=None)
        self.pending_path = self.root / ".central_mind" / "intake_pending.json"
        self.pending_path.parent.mkdir(parents=True, exist_ok=True)
        self.pending_path.write_text("pending proposal", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def proposal(self, domain="Gen"):
        return {
            "domain": domain,
            "title": "Approved intake test",
            "content": "A test-only approved memory entry.",
            "tags": ["intake-test"],
            "kind": "fact",
            "originator": [{"type": "trainer", "name": "user"}],
        }

    def test_intake_submission_creates_pending_proposal_not_memory(self):
        result = self.tool.call({
            "proposal": self.proposal("Trd"),
            "memory_bridge": self.intake_client,
        })

        self.assertTrue(result["ok"], result.get("error"))
        data = result["data"]
        self.assertTrue(data["proposal_id"])
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["domain"], "Trd")
        self.assertEqual(self.memory.count(), 0)
        self.assertTrue(self.pending_path.exists())

        pending = self.service.pending_knowledge_proposals()
        self.assertTrue(any(
            p["proposal_id"] == data["proposal_id"] for p in pending
        ))

    def test_intake_memory_is_created_only_after_central_approval(self):
        result = self.tool.call({
            "proposal": self.proposal("Trd"),
            "memory_bridge": self.intake_client,
        })
        self.assertTrue(result["ok"], result.get("error"))
        proposal_id = result["data"]["proposal_id"]

        with self.assertRaises(PermissionError):
            self.service.commit_approved_proposal(
                proposal_id,
                approved_by="central_mind",
                decision_reason="Central Mind must not manufacture Raw.",
                approved_class="raw",
            )
        self.assertEqual(self.memory.count(), 0)
        self.assertTrue(self.pending_path.exists())

    def test_invalid_domain_does_not_create_memory(self):
        result = self.tool.call({
            "proposal": self.proposal("NOT_A_DOMAIN"),
            "memory_bridge": self.intake_client,
        })

        self.assertFalse(result["ok"])
        self.assertIn("proposal submission failed", result["error"])
        self.assertEqual(self.memory.summary()["total"], 0)
        self.assertTrue(self.pending_path.exists())

    def test_missing_client_does_not_create_memory(self):
        result = self.tool.call({
            "proposal": self.proposal(),
            "memory_bridge": None,
        })

        self.assertFalse(result["ok"])
        self.assertEqual(self.memory.summary()["total"], 0)
        self.assertTrue(self.pending_path.exists())


if __name__ == "__main__":
    unittest.main()
