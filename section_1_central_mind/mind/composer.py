"""The Composer.

Merges responses from multiple organs into one. Knows only the
response shape. Never the meaning.
"""
from __future__ import annotations

from typing import Any, Dict, List


class Composer:

    def combine(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        outputs: List[Any] = []
        questions: List[Dict[str, Any]] = []
        artifacts: List[Any] = []
        errors: List[str] = []

        for r in responses:
            status = r.get("status", "ok")

            if status == "ok":
                if "output" in r:
                    outputs.append(r["output"])
                if "artifacts" in r:
                    artifacts.extend(r.get("artifacts", []))

            elif status == "needs_answers":
                questions.extend(r.get("questions", []))

            elif status == "no_handler":
                continue

            elif status == "error":
                errors.append(r.get("error", "(unknown error)"))

        if questions:
            return {"status": "needs_answers", "questions": questions}
        if errors:
            return {"status": "error", "errors": errors, "outputs": outputs}
        if not outputs:
            return {"status": "no_handler"}

        return {
            "status": "ok",
            "output": self._merge_outputs(outputs),
            "outputs": outputs,
            "artifacts": artifacts,
        }

    def _merge_outputs(self, outputs: List[Any]) -> Any:
        if len(outputs) == 1:
            return outputs[0]
        # If every output is a string, join them.
        if all(isinstance(o, str) for o in outputs):
            return "\n\n".join(outputs)
        # Otherwise return the list.
        return outputs