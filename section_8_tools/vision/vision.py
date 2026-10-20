"""Vision tools.

Four tools:
  image_describe(path, question)   - describe or answer about an image
  image_read_text(path)            - OCR: extract text from an image
  pdf_read(path)                   - extract text from a PDF
  video_extract_frames(path, fps)  - extract frames as images

Uses qwen3-vl:8b on Ollama. No external API. Runs locally.
"""
from __future__ import annotations

import base64
import json
import re
import subprocess
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

from _base.tool import Tool
from _base.paths import missing_parent_directories
from guard.contract import ToolEffect


OLLAMA_URL = "http://localhost:11434"
VISION_MODEL = "qwen3-vl:8b"


def _encode_image_b64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _call_vision(prompt: str, image_b64: str, timeout: int = 180) -> str:
    payload = {
        "model": VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "images": [image_b64],
            }
        ],
        "stream": False,
        "options": {"num_predict": 1024},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        parsed = json.loads(resp.read().decode("utf-8"))
        return parsed.get("message", {}).get("content", "")


class ImageDescribe(Tool):
    name = "image_describe"
    description = (
        "Look at an image and describe it, or answer a question "
        "about it. Uses the local vision model."
    )
    parameters = {
        "path": "path to the image file (relative to workspace or absolute)",
        "question": "optional question about the image",
    }

    def effects(self, args: Dict[str, Any]) -> tuple[ToolEffect, ...]:
        rel = (args.get("path") or "").strip()
        if not rel:
            raise ValueError("path is required")
        target = self._resolve(rel)

        return (
            ToolEffect(
                action="read",
                target=str(target),
                scope="exact",
            ),
            ToolEffect(
                action="service",
                target=f"ollama:{VISION_MODEL}",
                scope="service",
            ),
        )

    def call(self, args: Dict[str, Any]) -> Dict[str, Any]:
        rel = (args.get("path") or "").strip()
        question = (args.get("question") or "").strip()

        if not rel:
            return {"ok": False, "data": None, "error": "path is required"}

        try:
            target = self._resolve(rel)
        except ValueError as e:
            return {"ok": False, "data": None, "error": str(e)}

        if not target.exists():
            return {"ok": False, "data": None, "error": f"not found: {rel}"}

        try:
            image_b64 = _encode_image_b64(target)
        except Exception as e:
            return {"ok": False, "data": None, "error": f"read failed: {e}"}

        prompt = question or "Describe this image in detail. What do you see?"
        try:
            reply = _call_vision(prompt, image_b64)
        except Exception as e:
            return {"ok": False, "data": None, "error": f"vision model error: {e}"}

        return {
            "ok": True,
            "data": {
                "path": str(target),
                "question": question or "(describe)",
                "answer": reply,
            },
            "error": None,
        }


class ImageReadText(Tool):
    name = "image_read_text"
    description = (
        "Read text from an image (OCR). Handles screenshots, scans, "
        "and photographed documents. Works for any script, including "
        "Urdu, Arabic, Chinese, Hindi."
    )
    parameters = {
        "path": "path to the image file",
    }

    def effects(self, args: Dict[str, Any]) -> tuple[ToolEffect, ...]:
        rel = (args.get("path") or "").strip()
        if not rel:
            raise ValueError("path is required")
        target = self._resolve(rel)

        return (
            ToolEffect(
                action="read",
                target=str(target),
                scope="exact",
            ),
            ToolEffect(
                action="service",
                target=f"ollama:{VISION_MODEL}",
                scope="service",
            ),
        )

    def call(self, args: Dict[str, Any]) -> Dict[str, Any]:
        rel = (args.get("path") or "").strip()
        if not rel:
            return {"ok": False, "data": None, "error": "path is required"}

        try:
            target = self._resolve(rel)
        except ValueError as e:
            return {"ok": False, "data": None, "error": str(e)}

        if not target.exists():
            return {"ok": False, "data": None, "error": f"not found: {rel}"}

        try:
            image_b64 = _encode_image_b64(target)
        except Exception as e:
            return {"ok": False, "data": None, "error": f"read failed: {e}"}

        prompt = (
            "Extract all text visible in this image. Return only the "
            "text, preserving line breaks and structure. Do not add "
            "commentary. If the text is in a non-Latin script, keep "
            "it in its original script and also provide a "
            "transliteration on the next line."
        )
        try:
            reply = _call_vision(prompt, image_b64)
        except Exception as e:
            return {"ok": False, "data": None, "error": f"vision model error: {e}"}

        return {
            "ok": True,
            "data": {
                "path": str(target),
                "text": reply,
            },
            "error": None,
        }


class PdfRead(Tool):
    name = "pdf_read"
    description = (
        "Extract text from a PDF. If the PDF has embedded text, "
        "uses pdfplumber. If it is scanned (images), falls back to "
        "vision OCR on rendered pages."
    )
    parameters = {
        "path": "path to the PDF file",
        "pages": "optional page range, e.g. '1-5' or 'all'",
    }

    def effects(self, args: Dict[str, Any]) -> tuple[ToolEffect, ...]:
        rel = (args.get("path") or "").strip()
        if not rel:
            raise ValueError("path is required")
        target = self._resolve(rel)

        return (
            ToolEffect(
                action="read",
                target=str(target),
                scope="exact",
            ),
        )

    def call(self, args: Dict[str, Any]) -> Dict[str, Any]:
        rel = (args.get("path") or "").strip()
        if not rel:
            return {"ok": False, "data": None, "error": "path is required"}

        try:
            target = self._resolve(rel)
        except ValueError as e:
            return {"ok": False, "data": None, "error": str(e)}

        if not target.exists():
            return {"ok": False, "data": None, "error": f"not found: {rel}"}

        try:
            import pdfplumber
        except ImportError:
            return {
                "ok": False,
                "data": None,
                "error": "pdfplumber is not installed. "
                         "Run: pip3 install pdfplumber",
            }

        pages_arg = (args.get("pages") or "all").strip()

        try:
            with pdfplumber.open(str(target)) as pdf:
                total = len(pdf.pages)
                if pages_arg == "all":
                    indices = range(total)
                else:
                    m = re.match(r"^(\d+)-(\d+)$", pages_arg)
                    if not m:
                        return {
                            "ok": False,
                            "data": None,
                            "error": "pages must be 'all' or 'N-M'",
                        }
                    start = max(1, int(m.group(1))) - 1
                    end = min(total, int(m.group(2)))
                    indices = range(start, end)

                chunks = []
                for i in indices:
                    page = pdf.pages[i]
                    page_text = page.extract_text() or ""
                    chunks.append(f"----- page {i + 1} -----")
                    chunks.append(page_text)
                    chunks.append("")
                full_text = "\n".join(chunks)
        except Exception as e:
            return {"ok": False, "data": None, "error": f"pdf read failed: {e}"}

        # If the PDF yielded almost nothing, it is likely scanned.
        if len(full_text.strip()) < 50:
            return {
                "ok": True,
                "data": {
                    "path": str(target),
                    "note": (
                        "PDF appears to be scanned. Vision OCR fallback "
                        "is not yet wired in. Extract pages as images "
                        "and use image_read_text."
                    ),
                    "text": full_text,
                },
                "error": None,
            }

        return {
            "ok": True,
            "data": {
                "path": str(target),
                "pages_read": len(list(indices)),
                "text": full_text,
            },
            "error": None,
        }


class VideoExtractFrames(Tool):
    name = "video_extract_frames"
    description = (
        "Extract frames from a video as PNG images. Each frame can "
        "then be passed to image_describe or image_read_text."
    )
    parameters = {
        "path": "path to the video file",
        "fps": "optional frames per second, default 1",
        "max_frames": "optional cap, default 30",
    }

    def effects(self, args: Dict[str, Any]) -> tuple[ToolEffect, ...]:
        rel = (args.get("path") or "").strip()
        if not rel:
            raise ValueError("path is required")

        target = self._resolve(rel)
        out_dir = (
            self.workspace_root
            / ".central_mind"
            / "frames"
        ).resolve()

        effects = [
            ToolEffect(
                action="read",
                target=str(target),
                scope="exact",
            ),
        ]

        # mkdir(parents=True) may create ancestors of frames. Declare
        # every such mutation explicitly; tree scope never reaches upward.
        effects.extend(
            ToolEffect(
                action="create",
                target=str(parent),
                scope="exact",
            )
            for parent in missing_parent_directories(
                self.workspace_root,
                out_dir,
            )
        )

        if not out_dir.exists():
            effects.append(
                ToolEffect(
                    action="create",
                    target=str(out_dir),
                    scope="exact",
                )
            )

        # ffmpeg -y may create new frame files or overwrite existing
        # matching frame files below this directory.
        effects.append(
            ToolEffect(
                action="write",
                target=str(out_dir),
                scope="tree",
            )
        )

        effects.append(
            ToolEffect(
                action="execute",
                target="ffmpeg",
                scope="service",
            )
        )

        return tuple(effects)

    def call(self, args: Dict[str, Any]) -> Dict[str, Any]:
        rel = (args.get("path") or "").strip()
        if not rel:
            return {"ok": False, "data": None, "error": "path is required"}

        try:
            target = self._resolve(rel)
        except ValueError as e:
            return {"ok": False, "data": None, "error": str(e)}

        if not target.exists():
            return {"ok": False, "data": None, "error": f"not found: {rel}"}

        fps = float(args.get("fps") or 1)
        max_frames = int(args.get("max_frames") or 30)

        out_dir = self.workspace_root / ".central_mind" / "frames"
        out_dir.mkdir(parents=True, exist_ok=True)

        pattern = str(out_dir / f"{target.stem}_%04d.png")

        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(target),
            "-vf", f"fps={fps}",
            "-frames:v", str(max_frames),
            pattern,
        ]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180,
            )
        except FileNotFoundError:
            return {
                "ok": False,
                "data": None,
                "error": "ffmpeg is not installed. "
                         "Run: brew install ffmpeg",
            }
        except Exception as e:
            return {"ok": False, "data": None, "error": f"extract failed: {e}"}

        if proc.returncode != 0:
            return {
                "ok": False,
                "data": None,
                "error": f"ffmpeg error: {proc.stderr[:400]}",
            }

        frames = sorted(out_dir.glob(f"{target.stem}_*.png"))

        return {
            "ok": True,
            "data": {
                "source": str(target),
                "fps": fps,
                "frame_count": len(frames),
                "frames": [str(p.relative_to(self.workspace_root)) for p in frames],
            },
            "error": None,
        }


TOOLS = [ImageDescribe, ImageReadText, PdfRead, VideoExtractFrames]
