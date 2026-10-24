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
            actor="trainer-user",
            role="trainer",
            domain="Gen",
        )
        self.central_client = self.service.client(
            actor="central_mind",
            role="central_mind",
            domain="Mind",
        )
        self.coding_client = self.service.client(
            actor="coder",
            role="domain",
            domain="Cod",
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

    def test_trainer_intake_creates_unverified_raw_memory_with_context(self):
        proposal = self.proposal("Trd")
        proposal.update({
            "source_path": "lesson.txt",
            "intake_context": [{
                "question": "What is this material?",
                "answer": "A training example for testing.",
            }],
        })
        result = self.tool.call({
            "proposal": proposal,
            "memory_bridge": self.intake_client,
        })

        self.assertTrue(result["ok"], result.get("error"))
        data = result["data"]
        self.assertTrue(data["memory_id"])
        self.assertTrue(data["memory_id"].startswith("raw_"))
        self.assertEqual(data["status"], "stored_raw")
        self.assertEqual(data["memory_class"], "raw")
        self.assertEqual(data["domain"], "Trd")
        self.assertEqual(self.memory.count(), 1)
        entry = self.memory.get(data["memory_id"])
        self.assertEqual(entry.memory_class, "raw")
        self.assertEqual(entry.domain_created, "Trd")
        self.assertEqual(entry.originator[0].name, "trainer-user")
        self.assertIn("A test-only approved memory entry.", entry.content)
        self.assertIn("A training example for testing.", entry.content)
        self.assertEqual(entry.source["source_type"], "intake")
        self.assertEqual(entry.readers, ["central_mind"])
        self.assertTrue(
            (self.root / "memory" / "Raw Memory" / f"{entry.id}.json").is_file()
        )
        recalled = self.central_client.recall(
            query="training example for testing",
            memory_class="raw",
        )
        self.assertEqual([item["id"] for item in recalled], [data["memory_id"]])
        self.assertEqual(recalled[0]["memory_class"], "raw")
        self.assertEqual(
            self.coding_client.recall(query="training example for testing"),
            [],
        )
        self.assertEqual(
            self.coding_client.recall(
                query="training example for testing",
                memory_class="raw",
            ),
            [],
        )
        self.assertIsNone(self.coding_client.get(data["memory_id"]))

    def test_trainer_intake_stores_content_larger_than_previous_limit(self):
        content = ("large training source\n" * 29_999) + "END"
        proposal = self.proposal()
        proposal["content"] = content
        proposal["intake_context"] = [{
            "question": "What is this material?",
            "answer": "A large training source used to verify intake has no size cap.",
        }]

        result = self.tool.call({
            "proposal": proposal,
            "memory_bridge": self.intake_client,
        })

        self.assertTrue(result["ok"], result.get("error"))
        entry = self.memory.get(result["data"]["memory_id"])
        self.assertIn(content, entry.content)
        self.assertGreater(len(entry.content.encode("utf-8")), 512 * 1024)

    def test_non_trainer_cannot_create_raw_intake_memory(self):
        user_client = self.service.client(
            actor="regular-user",
            role="user",
            domain="Gen",
        )
        proposal = self.proposal()
        proposal["intake_context"] = [{
            "question": "What is this material?",
            "answer": "A user supplied source.",
        }]
        result = self.tool.call({
            "proposal": proposal,
            "memory_bridge": user_client,
        })
        self.assertFalse(result["ok"])
        self.assertIn("trainer role required", result["error"].lower())
        self.assertEqual(self.memory.count(), 0)

    def test_intake_requires_trainer_context(self):
        result = self.tool.call({
            "proposal": self.proposal(),
            "memory_bridge": self.intake_client,
        })
        self.assertFalse(result["ok"])
        self.assertIn("nature of the material", result["error"])
        self.assertEqual(self.memory.count(), 0)

    def test_invalid_domain_does_not_create_memory(self):
        result = self.tool.call({
            "proposal": self.proposal("NOT_A_DOMAIN"),
            "memory_bridge": self.intake_client,
        })

        self.assertFalse(result["ok"])
        self.assertIn("Raw Memory intake failed", result["error"])
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
