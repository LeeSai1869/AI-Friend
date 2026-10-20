from __future__ import annotations

from typing import Dict


class InspectionAnalyzer:
    """Read and analyze evidence selected from the real project."""

    MAX_CONTENT_CHARACTERS = 12000

    def read_selected(
        self,
        *,
        selected_files,
        broker,
    ) -> Dict[str, str]:
        inspected: Dict[str, str] = {}

        for file_path in selected_files:
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

                inspected[file_path] = str(content)[
                    :self.MAX_CONTENT_CHARACTERS
                ]

        return inspected

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
            "anything was modified. Do not invent paths."
        )

        return str(
            caller.call(
                "coder_model",
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )
        ).strip()
