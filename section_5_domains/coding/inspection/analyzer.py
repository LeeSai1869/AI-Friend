from __future__ import annotations

from ..cognition import request_model

import json
import re
from typing import Dict, Optional


class InspectionAnalyzer:
    """Read and analyze evidence selected from the real project."""

    MAX_CONTENT_CHARACTERS = 12000
    MAX_TOTAL_CHARACTERS = 48000

    def read_selected(
        self,
        *,
        selected_files,
        broker,
        remaining_characters: Optional[int] = None,
    ) -> Dict[str, str]:
        inspected: Dict[str, str] = {}
        self.last_truncated_files = []
        self.last_read_errors = {}
        remaining = (
            self.MAX_TOTAL_CHARACTERS
            if remaining_characters is None
            else max(0, min(remaining_characters, self.MAX_TOTAL_CHARACTERS))
        )

        for file_path in selected_files:
            if remaining <= 0:
                self.last_truncated_files.append(file_path)
                continue
            result = broker.call(
                "read_file",
                {"path": file_path},
            )

            if result.get("ok"):
                content = (
                    (result.get("data") or {}).get(
                        "content",
                        "",
                    )
                )
                content = str(content)
                limit = min(self.MAX_CONTENT_CHARACTERS, remaining)
                inspected[file_path] = content[:limit]
                remaining -= len(inspected[file_path])
                if len(content) > limit:
                    self.last_truncated_files.append(file_path)
            else:
                self.last_read_errors[file_path] = str(
                    result.get("error") or "file read failed"
                )

        return inspected

    def assess(
        self,
        *,
        task: str,
        inspected: Dict[str, str],
        caller,
    ) -> Dict[str, str | bool]:
        """Return an initial answer and a concrete evidence-gap signal."""
        evidence = "\n\n".join(
            f"--- {path} ---\n{content}"
            for path, content in inspected.items()
        )
        prompt = (
            f"User task: {task}\n\n"
            f"Files actually inspected:\n{evidence}\n\n"
            "Answer using only this evidence. Do not claim that the whole "
            "project was inspected or that anything was modified. Decide "
            "whether the evidence is sufficient to answer the task. If not, "
            "name the specific missing context that another project-file "
            "inspection could resolve; do not ask for user-owned decisions. "
            "Return JSON only in this shape: "
            '{"answer": "grounded answer", "evidence_sufficient": true, '
            '"missing_context": "specific gap or empty string"}.'
        )
        reply = str(request_model(
            caller,
            capability="plan",
            messages=[{"role": "user", "content": prompt}],
        )).strip()

        payload = self._parse_object(reply)
        if (
            not isinstance(payload, dict)
            or not isinstance(payload.get("answer"), str)
            or type(payload.get("evidence_sufficient")) is not bool
            or not isinstance(payload.get("missing_context"), str)
        ):
            return {
                "answer": reply,
                "evidence_sufficient": True,
                "missing_context": "",
            }
        return payload

    def analyze(
        self,
        *,
        task: str,
        inspected: Dict[str, str],
        caller,
    ) -> str:
        evidence = "\n\n".join(
            f"--- {path} ---\n{content}"
            for path, content in inspected.items()
        )

        prompt = (
            f"User task: {task}\n\n"
            f"Files actually inspected:\n{evidence}\n\n"
            "Answer using only the inspected project evidence. "
            "Identify the relevant file or files and explain why "
            "they are relevant. If the evidence is insufficient, "
            "say exactly what remains unknown. Do not claim that "
            "anything was modified. Do not invent paths or claim "
            "that the whole project was inspected."
        )

        return str(
            request_model(caller,
                capability="plan",
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )
        ).strip()

    @staticmethod
    def _parse_object(reply: str) -> Optional[dict]:
        try:
            payload = json.loads(reply)
            return payload if isinstance(payload, dict) else None
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", reply, re.DOTALL)
            if match is None:
                return None
            try:
                payload = json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
            return payload if isinstance(payload, dict) else None
