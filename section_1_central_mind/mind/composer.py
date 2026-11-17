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
        failure_outputs: List[str] = []
        failed_responses: List[Dict[str, Any]] = []

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
                failed_responses.append(r)
                output = r.get("output")
                if isinstance(output, str) and output.strip():
                    failure_outputs.append(output.strip())

        if questions:
            return {"status": "needs_answers", "questions": questions}
        if errors:
            result = {"status": "error", "errors": errors, "outputs": outputs}
            if failure_outputs:
                result["output"] = "\n\n".join(failure_outputs)
            for field in ("execution_receipt", "attempts", "functional_tests"):
                values = [r[field] for r in failed_responses if field in r]
                if len(values) == 1:
                    result[field] = values[0]
                elif values:
                    result[f"{field}_by_response"] = values
            return result
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