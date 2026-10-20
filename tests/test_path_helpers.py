import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = PROJECT_ROOT / "section_8_tools"
sys.path.insert(0, str(TOOLS_DIR))

from _base.paths import missing_parent_directories  # noqa: E402


class PathHelperTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        (self.root / "workspace").mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_returns_only_missing_parents(self):
        existing = self.root / "workspace" / "existing"
        existing.mkdir()

        target = existing / "a" / "b" / "file.txt"

        self.assertEqual(
            missing_parent_directories(
                self.root,
                target,
            ),
            (
                existing / "a",
                existing / "a" / "b",
            ),
        )

    def test_excludes_target_itself(self):
        target = self.root / "workspace" / "new_folder"

        self.assertEqual(
            missing_parent_directories(
                self.root,
                target,
            ),
            (),
        )

    def test_follows_existing_symlink(self):
        real = self.root / "workspace" / "real"
        real.mkdir()

        link = self.root / "workspace" / "link"

        try:
            link.symlink_to(
                real,
                target_is_directory=True,
            )
        except (OSError, NotImplementedError) as exc:
            self.skipTest(
                f"Symlinks unavailable: {exc}"
            )

        target = link / "a" / "b" / "file.txt"

        self.assertEqual(
            missing_parent_directories(
                self.root,
                target,
            ),
            (
                real / "a",
                real / "a" / "b",
            ),
        )

    def test_escape_fails_neutrally(self):
        outside = (
            self.root.parent
            / "outside"
            / "file.txt"
        )

        with self.assertRaises(ValueError):
            missing_parent_directories(
                self.root,
                outside,
            )

    def test_result_is_immutable_tuple(self):
        target = (
            self.root
            / "workspace"
            / "a"
            / "b"
            / "file.txt"
        )

        result = missing_parent_directories(
            self.root,
            target,
        )

        self.assertIsInstance(result, tuple)


if __name__ == "__main__":
    unittest.main()
