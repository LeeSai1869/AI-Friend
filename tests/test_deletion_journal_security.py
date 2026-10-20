import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from section_3_memory.api import Memory
from section_3_memory.service import MemoryService


class DeletionJournalSecurityTests(unittest.TestCase):
    def test_corrupt_journal_fails_closed(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            memory = Memory(root=root)
            service = MemoryService(memory)
            journal = service._deletion_journal

            journal.write_text("{not valid JSON", encoding="utf-8")

            with self.assertRaisesRegex(
                RuntimeError, "Cannot safely load deletion proposal journal"
            ):
                MemoryService(Memory(root=root))

    def test_invalid_journal_schema_fails_closed(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            service = MemoryService(Memory(root=root))
            service._deletion_journal.write_text(
                json.dumps({
                    "version": 99,
                    "next_proposal_id": 1,
                    "proposals": [],
                }),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                RuntimeError, "Cannot safely load deletion proposal journal"
            ):
                MemoryService(Memory(root=root))


if __name__ == "__main__":
    unittest.main()
