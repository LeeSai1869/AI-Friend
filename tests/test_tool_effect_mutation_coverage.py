import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "section_8_tools"

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))


from section_8_tools.filesystem.filesystem import WriteFile
from section_8_tools.folders.folders import CreateFolder
from section_8_tools.scaffold.scaffold import ApplyScaffold
from section_8_tools.vision.vision import VideoExtractFrames


class ToolEffectMutationCoverageTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()

    def tearDown(self):
        self.tmp.cleanup()

    def tool(self, cls):
        return cls(self.root, broker=None)

    def snapshot(self):
        return {
            path.resolve()
            for path in self.root.rglob("*")
        }

    def declared_creates(self, effects):
        return {
            Path(effect.target).resolve()
            for effect in effects
            if effect.action == "create"
        }

    def assert_creations_covered(
        self,
        *,
        before,
        after,
        effects,
    ):
        actual_created = after - before
        declared_created = self.declared_creates(effects)

        missing = actual_created - declared_created

        self.assertFalse(
            missing,
            "Actual filesystem creations were not declared:\n"
            + "\n".join(
                f"  {path}"
                for path in sorted(
                    missing,
                    key=str,
                )
            ),
        )

    def test_write_file_covers_every_actual_creation(self):
        tool = self.tool(WriteFile)

        args = {
            "path": "alpha/beta/file.txt",
            "content": "hello",
        }

        before = self.snapshot()
        effects = tool.effects(args)

        result = tool.call(args)

        self.assertTrue(result["ok"], result)

        after = self.snapshot()

        self.assert_creations_covered(
            before=before,
            after=after,
            effects=effects,
        )

    def test_create_folder_covers_every_actual_creation(self):
        tool = self.tool(CreateFolder)

        args = {
            "path": "alpha/beta/gamma",
        }

        before = self.snapshot()
        effects = tool.effects(args)

        result = tool.call(args)

        self.assertTrue(result["ok"], result)

        after = self.snapshot()

        self.assert_creations_covered(
            before=before,
            after=after,
            effects=effects,
        )

    def test_apply_scaffold_covers_every_actual_creation(self):
        scaffold_root = (
            self.root
            / "section_10_workspace"
            / "scaffolds"
            / "demo"
        )

        sources = scaffold_root / "sources"
        sources.mkdir(parents=True)

        source_file = sources / "main.txt"
        source_file.write_text(
            "hello",
            encoding="utf-8",
        )

        manifest = scaffold_root / "scaffold.json"
        manifest.write_text(
            json.dumps({
                "name": "demo",
                "dirs": [
                    "generated/one/two",
                ],
                "files": [
                    {
                        "path": "generated/one/two/main.txt",
                        "source": "main.txt",
                        "overwrite": False,
                    }
                ],
            }),
            encoding="utf-8",
        )

        tool = self.tool(ApplyScaffold)
        args = {"name": "demo"}

        # Scaffold source material already exists before the operation,
        # so only destination-side mutations can appear in the delta.
        before = self.snapshot()
        effects = tool.effects(args)

        result = tool.call(args)

        self.assertTrue(result["ok"], result)

        after = self.snapshot()

        self.assert_creations_covered(
            before=before,
            after=after,
            effects=effects,
        )

    def test_video_extract_covers_python_side_directory_creations(self):
        source = self.root / "movie.mp4"
        source.write_bytes(b"not-a-real-video")

        tool = self.tool(VideoExtractFrames)
        args = {
            "path": "movie.mp4",
            "fps": 1,
            "max_frames": 1,
        }

        before = self.snapshot()
        effects = tool.effects(args)

        class FakeProcess:
            returncode = 0
            stderr = ""

        with patch(
            "section_8_tools.vision.vision.subprocess.run",
            return_value=FakeProcess(),
        ):
            result = tool.call(args)

        self.assertTrue(result["ok"], result)

        after = self.snapshot()

        self.assert_creations_covered(
            before=before,
            after=after,
            effects=effects,
        )

        frames_root = (
            self.root / ".central_mind" / "frames"
        ).resolve()

        writes = [
            effect
            for effect in effects
            if effect.action == "write"
        ]

        self.assertEqual(len(writes), 1)
        self.assertEqual(
            Path(writes[0].target).resolve(),
            frames_root,
        )
        self.assertEqual(writes[0].scope, "tree")

    def test_existing_write_is_declared_write_not_create(self):
        target = self.root / "existing.txt"
        target.write_text(
            "old",
            encoding="utf-8",
        )

        tool = self.tool(WriteFile)

        args = {
            "path": "existing.txt",
            "content": "new",
        }

        effects = tool.effects(args)

        matching = [
            effect
            for effect in effects
            if Path(effect.target).resolve() == target.resolve()
        ]

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].action, "write")

        before = self.snapshot()

        result = tool.call(args)

        self.assertTrue(result["ok"], result)
        self.assertEqual(
            target.read_text(encoding="utf-8"),
            "new",
        )

        after = self.snapshot()

        self.assertEqual(after - before, set())


if __name__ == "__main__":
    unittest.main()
