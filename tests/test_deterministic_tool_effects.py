from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

# Tool modules use the runtime import convention "_base.tool".
# ToolBroker establishes this path before importing tools; reproduce
# that same environment here without changing production imports.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = PROJECT_ROOT / "section_8_tools"

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from section_8_tools.filesystem.filesystem import (
    ListFiles,
    ReadFile,
    SearchFiles,
    WriteFile,
)
from section_8_tools.folders.folders import CreateFolder
from section_8_tools.intake.intake import (
    IntakeCommit,
    IntakePropose,
)
from section_8_tools.scaffold.scaffold import (
    ApplyScaffold,
    ListScaffolds,
    ReadScaffold,
)
from section_8_tools.terminal.terminal import RunCommand
from section_8_tools.vision.vision import (
    DocumentRead,
    ImageDescribe,
    ImageReadText,
    PdfRead,
    VideoExtractFrames,
    VideoRead,
)
from section_8_tools.web.web import WebFetch, WebSearch


class DeterministicToolEffectTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()

    def tearDown(self):
        self.tmp.cleanup()

    def tool(self, cls):
        return cls(self.root, broker=None)

    def test_filesystem_read_effects(self):
        target = self.root / "example.txt"
        target.write_text("hello", encoding="utf-8")

        effect = self.tool(ReadFile).effects({
            "path": "example.txt",
        })[0]

        self.assertEqual(effect.action, "read")
        self.assertEqual(effect.target, str(target))
        self.assertEqual(effect.scope, "exact")

        listed = self.tool(ListFiles).effects({})[0]
        self.assertEqual(listed.action, "read")
        self.assertEqual(listed.target, str(self.root))
        self.assertEqual(listed.scope, "children")

        searched = self.tool(SearchFiles).effects({
            "pattern": "example",
        })[0]
        self.assertEqual(searched.action, "read")
        self.assertEqual(searched.target, str(self.root))
        self.assertEqual(searched.scope, "tree")

    def test_write_file_distinguishes_create_and_write(self):
        tool = self.tool(WriteFile)

        create_effect = tool.effects({
            "path": "new.txt",
            "content": "x",
        })[0]

        self.assertEqual(create_effect.action, "create")

        existing = self.root / "existing.txt"
        existing.write_text("old", encoding="utf-8")

        write_effect = tool.effects({
            "path": "existing.txt",
            "content": "new",
        })[0]

        self.assertEqual(write_effect.action, "write")

    def test_write_file_declares_missing_parent_creations(self):
        effects = self.tool(WriteFile).effects({
            "path": "one/two/file.txt",
            "content": "x",
        })

        self.assertEqual(
            [(e.action, e.target) for e in effects],
            [
                ("create", str(self.root / "one")),
                ("create", str(self.root / "one" / "two")),
                ("create", str(self.root / "one" / "two" / "file.txt")),
            ],
        )

    def test_create_folder_declares_all_missing_directories(self):
        effects = self.tool(CreateFolder).effects({
            "path": "one/two/three",
        })

        self.assertEqual(
            [(e.action, e.target) for e in effects],
            [
                ("create", str(self.root / "one")),
                ("create", str(self.root / "one" / "two")),
                ("create", str(self.root / "one" / "two" / "three")),
            ],
        )

    def test_create_folder_declares_create(self):
        effects = self.tool(CreateFolder).effects({
            "path": "a/b",
        })

        effect = effects[-1]

        self.assertEqual(effect.action, "create")
        self.assertEqual(
            effect.target,
            str(self.root / "a" / "b"),
        )

    def test_intake_propose_declares_source_read_and_classification_without_disk_write(self):
        folder = self.root / "source"
        folder.mkdir()
        (folder / "a.txt").write_text(
            "hello",
            encoding="utf-8",
        )

        effects = self.tool(IntakePropose).effects({
            "path": "source",
            "caller": object(),
        })

        self.assertEqual(
            [e.action for e in effects],
            ["service", "read"],
        )
        self.assertEqual(effects[1].scope, "tree")
        self.assertEqual(effects[0].target, "model:classification")

    def test_intake_commit_declares_memory_effect(self):
        effects = self.tool(IntakeCommit).effects({
            "proposal": {
                "content": "knowledge",
            },
        })

        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0].action, "memory")
        self.assertEqual(
            effects[0].target,
            "memory:raw_intake",
        )

    def _make_scaffold(self):
        base = (
            self.root
            / "section_10_workspace"
            / "scaffolds"
            / "demo"
        )
        sources = base / "sources"
        sources.mkdir(parents=True)

        (sources / "main.txt").write_text(
            "hello",
            encoding="utf-8",
        )

        (base / "scaffold.json").write_text(
            json.dumps({
                "name": "demo",
                "dirs": ["generated"],
                "files": [
                    {
                        "path": "generated/main.txt",
                        "source": "main.txt",
                        "overwrite": False,
                    }
                ],
            }),
            encoding="utf-8",
        )

        return base

    def test_scaffold_effects_include_sources_and_destinations(self):
        base = self._make_scaffold()

        listed = self.tool(ListScaffolds).effects({})
        self.assertEqual(listed[0].action, "read")
        self.assertEqual(listed[0].scope, "tree")

        read = self.tool(ReadScaffold).effects({
            "name": "demo",
        })
        self.assertEqual(
            read[0].target,
            str(base / "scaffold.json"),
        )

        applied = self.tool(ApplyScaffold).effects({
            "name": "demo",
        })

        self.assertEqual(
            [e.action for e in applied],
            ["read", "read", "create", "create"],
        )

        self.assertEqual(applied[1].scope, "tree")
        self.assertEqual(
            applied[2].target,
            str(self.root / "generated"),
        )
        self.assertEqual(
            applied[3].target,
            str(self.root / "generated" / "main.txt"),
        )

    def test_scaffold_effects_include_and_deduplicate_parent_creations(self):
        base = (
            self.root
            / "section_10_workspace"
            / "scaffolds"
            / "nested"
        )
        sources = base / "sources"
        sources.mkdir(parents=True)

        (sources / "main.txt").write_text(
            "hello",
            encoding="utf-8",
        )

        (base / "scaffold.json").write_text(
            json.dumps({
                "name": "nested",
                "dirs": ["alpha/beta"],
                "files": [
                    {
                        "path": "alpha/beta/main.txt",
                        "source": "main.txt",
                        "overwrite": False,
                    }
                ],
            }),
            encoding="utf-8",
        )

        effects = self.tool(ApplyScaffold).effects({
            "name": "nested",
        })

        creates = [
            e.target
            for e in effects
            if e.action == "create"
        ]

        self.assertEqual(
            creates,
            [
                str(self.root / "alpha"),
                str(self.root / "alpha" / "beta"),
                str(self.root / "alpha" / "beta" / "main.txt"),
            ],
        )

        self.assertEqual(len(creates), len(set(creates)))

    def test_vision_effects(self):
        image = self.root / "image.png"
        image.write_bytes(b"x")

        described = self.tool(ImageDescribe).effects({
            "path": "image.png",
        })

        self.assertEqual(
            [e.action for e in described],
            ["read", "service"],
        )
        self.assertTrue(
            described[1].target.startswith("ollama:")
        )

        ocr = self.tool(ImageReadText).effects({
            "path": "image.png",
        })

        self.assertEqual(
            [e.action for e in ocr],
            ["read", "service"],
        )

        pdf = self.tool(PdfRead).effects({
            "path": "doc.pdf",
        })
        self.assertEqual(
            [e.action for e in pdf],
            ["read", "service"],
        )

        document = self.tool(DocumentRead).effects({
            "name": "scan.pdf",
            "data_base64": "cGRm",
        })
        self.assertEqual(
            [effect.target for effect in document],
            ["document-reader", "ollama:qwen3-vl:8b"],
        )

        video_read = self.tool(VideoRead).effects({
            "name": "movie.mp4",
            "data_base64": "dmlkZW8=",
        })
        self.assertEqual(
            [effect.action for effect in video_read],
            ["execute", "service"],
        )

        video = self.tool(VideoExtractFrames).effects({
            "path": "movie.mp4",
        })

        self.assertEqual(
            [e.action for e in video],
            ["read", "create", "create", "write", "execute"],
        )

        runtime_root = (
            self.root / ".central_mind"
        ).resolve()
        frames_root = (
            runtime_root / "frames"
        ).resolve()

        self.assertEqual(
            Path(video[1].target).resolve(),
            runtime_root,
        )
        self.assertEqual(video[1].scope, "exact")

        self.assertEqual(
            Path(video[2].target).resolve(),
            frames_root,
        )
        self.assertEqual(video[2].scope, "exact")

        self.assertEqual(video[3].action, "write")
        self.assertEqual(
            Path(video[3].target).resolve(),
            frames_root,
        )
        self.assertEqual(video[3].scope, "tree")

        self.assertEqual(video[4].target, "ffmpeg")
        self.assertEqual(video[4].scope, "service")

    def test_web_effects(self):
        search = self.tool(WebSearch).effects({
            "query": "test",
        })

        self.assertEqual(search[0].action, "network")
        self.assertEqual(search[0].target, "web-search")

        fetch = self.tool(WebFetch).effects({
            "url": "example.com",
        })

        self.assertEqual(fetch[0].action, "network")
        self.assertEqual(
            fetch[0].target,
            "https://example.com",
        )

    def test_terminal_declares_execution_for_the_separate_guard_gate(self):
        effects = self.tool(RunCommand).effects({"command": ["python3", "-V"]})
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0].action, "execute")
        self.assertEqual(effects[0].target, "process:python3")
        self.assertEqual(effects[0].scope, "service")


if __name__ == "__main__":
    unittest.main(verbosity=2)
