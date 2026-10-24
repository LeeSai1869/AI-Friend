import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from section_3_memory.store import Store


class MemoryStoreSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.memory_root = Path(self.temp.name)
        self.entries_dir = self.memory_root / "entries"
        self.store = Store(self.memory_root)

    def tearDown(self):
        self.temp.cleanup()

    def test_accepts_valid_memory_id(self):
        path = self.store._path_for("mem_Cod_0000000000001")
        self.assertEqual(
            path,
            self.entries_dir / "mem_Cod_0000000000001.json",
        )

    def test_class_path_uses_named_memory_folder(self):
        path = self.store._path_for(
            "mem_Cod_0000000000001",
            "tested",
        )
        self.assertEqual(
            path,
            self.memory_root / "Tested Memory" / "mem_Cod_0000000000001.json",
        )

    def test_raw_memory_id_is_non_sequential(self):
        path = self.store._path_for(
            "raw_coding-rules_abcdefgh",
            "raw",
        )
        self.assertEqual(
            path,
            self.memory_root / "Raw Memory" / "raw_coding-rules_abcdefgh.json",
        )

    def test_rejects_parent_traversal(self):
        with self.assertRaises(ValueError):
            self.store._path_for("../outside")

    def test_rejects_path_separators_in_id(self):
        with self.assertRaises(ValueError):
            self.store._path_for("mem_Cod_../../outside")

    def test_rejects_unknown_domain(self):
        with self.assertRaises(ValueError):
            self.store._path_for("mem_BAD_0000000000001")

    def test_rejects_non_numeric_sequence(self):
        with self.assertRaises(ValueError):
            self.store._path_for("mem_Cod_abcdefghijklm")

    def test_rejects_wrong_sequence_length(self):
        with self.assertRaises(ValueError):
            self.store._path_for("mem_Cod_123")

    def test_rejects_malformed_id(self):
        with self.assertRaises(ValueError):
            self.store._path_for("not-a-memory-id")


if __name__ == "__main__":
    unittest.main()
