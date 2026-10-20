import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CENTRAL_MIND_DIR = PROJECT_ROOT / "section_1_central_mind"
sys.path.insert(0, str(CENTRAL_MIND_DIR))

from server import _is_within_root


class ServerPathSecurityTests(unittest.TestCase):
    def test_accepts_file_inside_project(self):
        with TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            target = root / "folder" / "file.txt"
            target.parent.mkdir()
            target.write_text("test", encoding="utf-8")
            self.assertTrue(_is_within_root(root, target))

    def test_accepts_project_root_itself(self):
        with TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            self.assertTrue(_is_within_root(root, root))

    def test_rejects_parent_traversal(self):
        with TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            root = base / "project"
            outside = base / "outside.txt"
            root.mkdir()
            outside.write_text("outside", encoding="utf-8")
            target = (root / "../outside.txt").resolve()
            self.assertFalse(_is_within_root(root, target))

    def test_rejects_sibling_with_shared_string_prefix(self):
        with TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            root = base / "project"
            sibling = base / "project_outside"
            root.mkdir()
            sibling.mkdir()
            target = sibling / "secret.txt"
            target.write_text("outside", encoding="utf-8")

            # Demonstrate why the old string-prefix check is unsafe.
            self.assertTrue(str(target.resolve()).startswith(str(root)))
            self.assertFalse(_is_within_root(root, target))

    def test_rejects_symlink_to_outside_file(self):
        with TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            root = base / "project"
            outside = base / "outside.txt"
            root.mkdir()
            outside.write_text("outside", encoding="utf-8")
            link = root / "linked.txt"

            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"Symlinks unavailable here: {exc}")

            self.assertFalse(_is_within_root(root, link))


if __name__ == "__main__":
    unittest.main()
