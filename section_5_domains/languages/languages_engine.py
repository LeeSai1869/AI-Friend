"""Languages domain — learn, read, translate, write.

Priority order (as defined by the trainer):
  1. Learn      — read documents, dictionaries, references; store
                  rules, vocabulary, formulas as raw memory.
  2. Read       — parse text in any known language into meaning.
  3. Translate  — convert between languages (natural or technical).
  4. Write      — produce output in a target language.

The mind uses this domain to communicate with the user in the
user's own language, and to understand commands in any language.

Language selection is automatic. No dropdown. No command. The
engine detects the input language and matches it on output.

Translation, reading, and writing go through the "translator"
model organ, not the "chat" model — because the translator is
optimized for cross-lingual work.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from mind.organ import Organ



# Map ISO codes to names. Aya and Gemma both confuse codes;
# names are more reliable.
LANGUAGE_NAMES = {
    "en": "English",
    "ur": "Urdu",
    "zh": "Mandarin Chinese",
    "hi": "Hindi",
    "es": "Spanish",
    "ar": "Arabic",
    "fr": "French",
    "de": "German",
    "ru": "Russian",
    "ja": "Japanese",
    "ko": "Korean",
    "pt": "Portuguese",
    "it": "Italian",
    "nl": "Dutch",
    "tr": "Turkish",
    "fa": "Persian",
    "he": "Hebrew",
}


def language_name(code: str) -> str:
    return LANGUAGE_NAMES.get((code or "").lower(), code or "")

LANGUAGES_FILE = Path(__file__).parent / "languages.json"
TRANSLATOR_ORGAN = "translator"


class LanguagesEngine(Organ):
    name = "languages"
    kind = "domain"
    scope = "outside_guards"
    capabilities = ["learn", "read", "translate", "write"]
    keywords = [
        "language", "translate", "translation", "urdu", "mandarin",
        "chinese", "hindi", "spanish", "arabic", "french", "german",
        "english", "script", "vocabulary", "grammar",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.languages = self._load_languages()

    def _load_languages(self) -> Dict[str, Any]:
        try:
            return json.loads(LANGUAGES_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"natural": [], "technical": []}

    def known_natural(self) -> List[Dict[str, str]]:
        return list(self.languages.get("natural", []))

    def known_technical(self) -> List[Dict[str, str]]:
        return list(self.languages.get("technical", []))

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        task = (request.get("task") or "").strip().lower()

        if task == "learn":
            return self._learn(request)
        if task == "read":
            return self._read(request)
        if task == "translate":
            return self._translate(request)
        if task == "write":
            return self._write(request)
        if task == "detect" or task == "":
            return self._detect(request)

        return {
            "status": "error",
            "error": f"unknown languages task: {task}",
        }

    # 1. LEARN
    def _learn(self, request: Dict[str, Any]) -> Dict[str, Any]:
        source = request.get("source") or request.get("path")
        language = request.get("language") or "unknown"

        return {
            "status": "ok",
            "output": (
                f"Learn requested.\n"
                f"Source: {source}\n"
                f"Language: {language}\n\n"
                "The mind should call the intake tool on this source. "
                "The intake tool classifies and stores it as raw memory. "
                "Language tag will be attached."
            ),
            "action": "call_intake",
            "intake_args": {
                "path": source,
                "language": language,
            },
        }

    # 2. READ
    def _read(self, request: Dict[str, Any]) -> Dict[str, Any]:
        text = request.get("text") or ""
        if not text:
            return {"status": "error", "error": "text is required"}

        caller = request.get("caller")
        if caller is None:
            return {
                "status": "error",
                "error": "caller is required to read text",
            }

        prompt = (
            "Read the following text and return its meaning in "
            "plain English, followed by any notable idioms, "
            "grammar structures, or language-specific features "
            "worth remembering.\n\n"
            f"TEXT:\n{text}\n\n"
            "Format your reply as:\n"
            "MEANING: <plain English meaning>\n"
            "FEATURES: <grammar / idioms / notes, one per line>"
        )

        try:
            reply = caller.route(
                domain="languages",
                capability="read",
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            return {"status": "error", "error": f"model failed: {e}"}

        return {"status": "ok", "output": reply}

    # 3. TRANSLATE
    def _translate(self, request: Dict[str, Any]) -> Dict[str, Any]:
        text = (request.get("text") or "").strip()
        target = (request.get("target") or "").strip()
        source = (request.get("source") or "").strip() or None

        if not text:
            return {"status": "error", "error": "text is required"}
        if not target:
            return {"status": "error", "error": "target language is required"}

        caller = request.get("caller")
        if caller is None:
            return {
                "status": "error",
                "error": "caller is required to translate",
            }

        source_name = language_name(source) if source else "auto-detect"
        target_name = language_name(target)
        if source:
            instruction = f"Translate from {source_name} to {target_name}."
        else:
            instruction = (
                f"Detect the source language, then translate to {target_name}."
            )

        prompt = (
            f"{instruction}\n\n"
            "Return ONLY the translation. No commentary, no notes, "
            "no source text. If a term has no direct equivalent, "
            "keep the original and add a bracketed gloss.\n\n"
            f"TEXT:\n{text}"
        )

        # Memory-first: if a tested translation exists for this
        # text + target, return it without calling an LLM.
        mem = request.get("memory")
        if mem is not None:
            try:
                hits = mem.recall(
                    query=f"translate {source or 'auto'}->{target}: {text[:60]}",
                    memory_class="tested",
                    domain="Lng",
                    tags=[f"{source or 'auto'}->{target}"],
                    limit=1,
                )
                if hits:
                    hit = hits[0]
                    return {
                        "status": "ok",
                        "output": hit["content"],
                        "target": target,
                        "source": source or "(detected)",
                        "source_model": (hit.get("source") or {}).get("name"),
                        "recalled_from_memory": hit.get("id"),
                    }
            except Exception:
                pass

        # Memory-first: if a tested translation exists for this
        # text + target, return it without calling an LLM.
        mem = request.get("memory")
        if mem is not None:
            try:
                hits = mem.recall(
                    query=f"translate {source or 'auto'}->{target}: {text[:60]}",
                    memory_class="tested",
                    domain="Lng",
                    tags=[f"{source or 'auto'}->{target}"],
                    limit=1,
                )
                if hits:
                    hit = hits[0]
                    return {
                        "status": "ok",
                        "output": hit["content"],
                        "target": target,
                        "source": source or "(detected)",
                        "source_model": (hit.get("source") or {}).get("name"),
                        "recalled_from_memory": hit.get("id"),
                    }
            except Exception:
                pass

        try:
            reply = caller.route(
                domain="languages",
                capability="translate",
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            return {"status": "error", "error": f"model failed: {e}"}

        # Attach source tag from the router.
        source_tag = None
        try:
            if hasattr(caller, "last_source") and caller.last_source:
                source_tag = dict(caller.last_source)
        except Exception:
            source_tag = None

        # Submit a candidate translation for Central Mind review.
        # Model output is not independently verified merely because it was generated.
        mem = request.get("memory")
        if mem is not None and source_tag is not None:
            try:
                mem.propose_knowledge(
                    domain="Lng",
                    title=f"translate {source or 'auto'}->{target}: {text[:60]}",
                    content=reply,
                    source=source_tag,
                    tags=["translation", f"{source or 'auto'}->{target}"],
                    kind="language",
                    requested_class="raw",
                    evidence={
                        "origin": "model-generated translation",
                        "independently_verified": False,
                    },
                    derivation_note=(
                        "Candidate translation; it has not been independently verified."
                    ),
                )
            except Exception as e:
                print(f"[languages] memory proposal failed: {e}")

        return {
            "status": "ok",
            "output": reply,
            "target": target,
            "source": source or "(detected)",
            "source_model": source_tag.get("name") if source_tag else None,
        }

    # 4. WRITE
    def _write(self, request: Dict[str, Any]) -> Dict[str, Any]:
        content = (request.get("content") or "").strip()
        target = (request.get("target") or "").strip()

        if not content:
            return {"status": "error", "error": "content is required"}
        if not target:
            return {"status": "error", "error": "target language is required"}

        caller = request.get("caller")
        if caller is None:
            return {
                "status": "error",
                "error": "caller is required to write",
            }

        prompt = (
            f"Rewrite the following content in {target}.\n"
            "Preserve meaning, tone, and structure. "
            "If the target is a programming language, output "
            "compilable code with no commentary.\n\n"
            f"CONTENT:\n{content}"
        )

        # Memory-first: if a tested entry exists for this text + target,
        # return it without calling an LLM.
        mem = request.get("memory")
        if mem is not None:
            try:
                # Use the bridge's recall to find matching translations.
                hits = mem.recall(
                    query=f"translate {source or 'auto'}->{target}: {text[:60]}",
                    domain="Lng",
                    memory_class="tested",
                    limit=3,
                )
                for hit in hits:
                    if (
                        hit.get("content")
                        and target in (hit.get("tags") or [])
                        or f"{source or 'auto'}->{target}" in (hit.get("tags") or [])
                    ):
                        return {
                            "status": "ok",
                            "output": hit["content"],
                            "target": target,
                            "source": source or "(detected)",
                            "source_model": (hit.get("source") or {}).get("name"),
                            "recalled_from_memory": hit.get("id"),
                        }
            except Exception:
                pass

        try:
            reply = caller.route(
                domain="languages",
                capability="write",
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            return {"status": "error", "error": f"model failed: {e}"}

        return {"status": "ok", "output": reply, "target": target}

    # DETECT
    def _detect(self, request: Dict[str, Any]) -> Dict[str, Any]:
        text = (request.get("text") or "").strip()
        if not text:
            return {"status": "error", "error": "text is required"}

        heuristic = self._heuristic_detect(text)
        if heuristic:
            return {
                "status": "ok",
                "output": heuristic,
                "method": "heuristic",
            }

        caller = request.get("caller")
        if caller is None:
            return {
                "status": "ok",
                "output": "en",
                "method": "default",
            }

        prompt = (
            "Detect the language of the following text. "
            "Reply with ONLY the ISO 639-1 code (e.g. 'en', 'ur', "
            "'zh', 'hi', 'es', 'ar', 'fr', 'de'). No prose.\n\n"
            f"TEXT:\n{text[:500]}"
        )

        try:
            reply = caller.route(
                domain="languages",
                capability="detect",
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception:
            return {"status": "ok", "output": "en", "method": "default"}

        code = reply.strip().lower()[:2]
        return {"status": "ok", "output": code, "method": "model"}

    def _heuristic_detect(self, text: str) -> Optional[str]:
        if re.search(r"[\u0600-\u06FF]", text):
            if re.search(r"[ٹڈڑںے]", text):
                return "ur"
            return "ar"
        if re.search(r"[\u0900-\u097F]", text):
            return "hi"
        if re.search(r"[\u4E00-\u9FFF]", text):
            return "zh"
        if re.search(r"[\u0400-\u04FF]", text):
            return "ru"
        return None


ORGAN = LanguagesEngine()
