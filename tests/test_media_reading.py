import base64
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

from section_8_tools.vision import vision
from section_8_tools.vision.vision import DocumentRead, VideoRead

CENTRAL_MIND_DIR = Path(__file__).resolve().parents[1] / "section_1_central_mind"
sys.path.insert(0, str(CENTRAL_MIND_DIR))

import server
from section_4_chatbox.runtime import ChatRuntime


def test_document_read_accepts_uploaded_text_without_writing(tmp_path):
    tool = DocumentRead(tmp_path, None)
    encoded = base64.b64encode(b"Central Mind source text").decode("ascii")

    result = tool.call({"name": "lesson.txt", "data_base64": encoded})

    assert result["ok"]
    assert result["data"]["text"] == "Central Mind source text"
    assert list(tmp_path.iterdir()) == []
    assert [effect.action for effect in tool.effects({
        "name": "lesson.txt",
        "data_base64": encoded,
    })] == ["service"]


def test_document_read_uses_ocr_for_scanned_pdf_pages(monkeypatch):
    class FakePixmap:
        def tobytes(self, image_format):
            assert image_format == "png"
            return b"rendered page"

    class FakePage:
        def get_text(self, kind):
            assert kind == "text"
            return ""

        def get_pixmap(self, **kwargs):
            assert kwargs["alpha"] is False
            return FakePixmap()

    class FakeDocument:
        needs_pass = False

        def __iter__(self):
            return iter([FakePage()])

        def __len__(self):
            return 1

        def __getitem__(self, index):
            assert index == 0
            return FakePage()

        def close(self):
            pass

    fake_fitz = SimpleNamespace(
        open=lambda **kwargs: FakeDocument(),
        Matrix=lambda x, y: (x, y),
    )
    monkeypatch.setitem(sys.modules, "pymupdf", fake_fitz)
    monkeypatch.setattr(
        vision,
        "_call_vision",
        lambda prompt, image, **kwargs: "Recognized words",
    )

    text = vision.read_document_bytes("scan.pdf", b"pdf bytes")

    assert "----- page 1 -----" in text
    assert "[OCR]\nRecognized words" in text


def test_document_read_ocr_failure_is_returned_to_the_caller(monkeypatch, tmp_path):
    def fail(_data):
        raise RuntimeError("Ollama is unavailable")

    monkeypatch.setattr(
        vision,
        "_read_pdf_bytes",
        fail,
    )
    tool = DocumentRead(tmp_path, None)
    result = tool.call({
        "name": "scan.pdf",
        "data_base64": base64.b64encode(b"pdf").decode("ascii"),
    })

    assert not result["ok"]
    assert "Ollama is unavailable" in result["error"]


def test_video_read_analyzes_every_sampled_frame(monkeypatch):
    written = []

    def fake_run(command, **kwargs):
        assert command[command.index("-vf") + 1] == "fps=2"
        pattern = command[-1]
        for index in range(3):
            frame_path = pattern.replace("%08d", f"{index + 1:08d}")
            with open(frame_path, "wb") as frame:
                frame.write(b"frame")
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr(vision, "_ffmpeg_executable", lambda: "ffmpeg")
    monkeypatch.setattr(vision.subprocess, "run", fake_run)
    monkeypatch.setattr(
        vision,
        "_ocr_image_bytes",
        lambda frame, prompt, **kwargs: written.append(frame) or "screen text and scene",
    )

    output = vision.read_video_bytes("lesson.mp4", b"video bytes", fps=2)

    assert len(written) == 3
    assert "frame at 0.00s" in output
    assert "frame at 0.50s" in output
    assert "frame at 1.00s" in output


def test_video_read_rejects_invalid_frame_rate_and_bad_base64(tmp_path):
    tool = VideoRead(tmp_path, None)
    invalid_fps = tool.call({
        "name": "clip.mp4",
        "data_base64": base64.b64encode(b"video").decode("ascii"),
        "fps": 0,
    })
    invalid_base64 = tool.call({
        "name": "clip.mp4",
        "data_base64": "not base64!",
    })

    assert not invalid_fps["ok"]
    assert "positive finite" in invalid_fps["error"]
    assert not invalid_base64["ok"]
    assert "valid base64" in invalid_base64["error"]


def test_vision_manifest_advertises_upload_readers():
    from section_8_tools.vision.__manifest__ import ORGAN

    assert "document_read" in ORGAN["capabilities"]
    assert "video_read" in ORGAN["capabilities"]
    assert "process.execute" in ORGAN["security"]["requires"]["video_read"]


def test_intake_routes_uploaded_video_and_documents_to_the_right_reader():
    class Broker:
        def __init__(self):
            self.calls = []

        def bind_central_mind(self):
            return self

        def call(self, name, args):
            self.calls.append((name, args))
            return {"ok": True, "data": {"text": "extracted contents"}}

    mind = SimpleNamespace(broker=Broker())
    video = asyncio.run(server._extract_uploaded_media(mind, {
        "name": "lesson.mov",
        "data_base64": "encoded video",
    }))
    document = asyncio.run(server._extract_uploaded_media(mind, {
        "name": "scan.pdf",
        "data_base64": "encoded document",
    }))

    assert video["name"] == "lesson.mov"
    assert video["content"] == "extracted contents"
    assert video["untrusted_source"] is True
    assert document["name"] == "scan.pdf"
    assert document["content"] == "extracted contents"
    assert [call[0] for call in mind.broker.calls] == ["video_read", "document_read"]


def test_chat_upload_reader_returns_extracted_contents_and_names():
    class Broker:
        def bind_central_mind(self):
            return self

        def call(self, name, args):
            assert name == "document_read"
            assert args["name"] == "notes.pdf"
            return {"ok": True, "data": {"text": "Extracted document text."}}

    mind = SimpleNamespace(broker=Broker())
    attachment = asyncio.run(server._extract_uploaded_media(mind, {
        "name": "notes.pdf",
        "data_base64": "cGRm",
    }))

    assert attachment["name"] == "notes.pdf"
    assert attachment["content"] == "Extracted document text."


def test_upload_batch_does_not_exhaust_reasoning_tool_budget():
    class BudgetedBroker:
        def __init__(self):
            self.budget = 1
            self.call_count = 0
            self.calls = []

        def bind_central_mind(self):
            return self

        def reset_budget(self):
            self.call_count = 0

        def call(self, name, args):
            if self.call_count >= self.budget:
                return {
                    "ok": False,
                    "error": f"tool budget exceeded ({self.budget})",
                }
            self.call_count += 1
            self.calls.append((name, args))
            return {"ok": True, "data": {"text": "extracted contents"}}

    mind = SimpleNamespace(broker=BudgetedBroker())
    sources = [
        {"name": f"source-{index}.svg", "data_base64": "encoded"}
        for index in range(21)
    ]

    attachments = asyncio.run(
        server._extract_uploaded_media_batch(mind, sources)
    )

    assert len(attachments) == len(sources)
    assert len(mind.broker.calls) == len(sources)
    assert mind.broker.call_count == 0


def test_attachment_only_chat_turn_reaches_central_mind_and_is_saved(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_FRIEND_STATE_DIR", str(tmp_path / "state"))

    class Mind:
        def __init__(self):
            self.input = None
            self.context = None

        def process(self, text, *, context):
            self.input = text
            self.context = context
            return {"status": "ok", "text": "I read the attached document."}

    mind = Mind()
    runtime = ChatRuntime(mind, tmp_path, owner="trainer")
    response = runtime.respond(
        "",
        attachments=[{
            "name": "notes.pdf",
            "content": "Extracted document text.",
            "untrusted_source": True,
        }],
    )

    assert response["ok"]
    assert mind.input == "Please review the attached file(s) and explain what they contain."
    assert mind.context["input"]["attachments"][0]["content"] == "Extracted document text."
    chat = runtime.load_chat(response["chat_id"])
    assert "[Attached files: notes.pdf]" in chat["turns"][0]["text"]
