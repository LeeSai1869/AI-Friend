import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from section_3_memory.api import Memory
from section_3_memory.service import MemoryService


class DeletionJournalTests(unittest.TestCase):
    def test_pending_deletion_survives_restart_without_deleting_memory(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            memory = Memory(root=root)
            service = MemoryService(memory)
            client = service.client(
                actor="coding", role="domain", domain="Cod"
            )

            entry = memory.record(
                domain="Cod",
                kind="fact",
                title="Keep this entry",
                content="A proposal must not delete this memory.",
            )
            proposal = client.propose_delete(
                entry.id, reason="Test restart persistence"
            )

            self.assertEqual(proposal["status"], "pending")
            self.assertTrue(memory.exists(entry.id))

            restarted_memory = Memory(root=root)
            restarted_service = MemoryService(restarted_memory)
            pending = restarted_service.pending_deletion_proposals()

            self.assertEqual(len(pending), 1)
            self.assertEqual(
                pending[0]["proposal_id"], proposal["proposal_id"]
            )
            self.assertEqual(pending[0]["memory_id"], entry.id)
            self.assertEqual(pending[0]["status"], "pending")
            self.assertTrue(restarted_memory.exists(entry.id))

            restarted_client = restarted_service.client(
                actor="coding", role="domain", domain="Cod"
            )
            next_proposal = restarted_client.propose_delete(
                entry.id, reason="Check proposal ID sequence"
            )
            self.assertEqual(
                next_proposal["proposal_id"],
                proposal["proposal_id"] + 1,
            )


if __name__ == "__main__":
    unittest.main()
