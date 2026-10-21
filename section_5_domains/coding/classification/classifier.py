from __future__ import annotations

from ..cognition import request_model, parse_object

from typing import Any, Dict


class CodingClassifier:
    """Classify a Coding request without executing it."""

    def classify(
        self,
        *,
        task: str,
        broker,
        caller,
        recalled_block: str = "",
    ) -> Dict[str, Any]:
        top = broker.call("list_files", {"path": ""})
        if not top.get("ok"):
            return {"kind": "error", "error": top.get("error") or "project listing failed"}
        top_entries = (top.get("data") or {}).get("entries", [])
        top_list = "\n".join(
            f"  {entry['path']}" for entry in top_entries
        )

        prompt = (
            f"Task: {task}\n\n"
            f"Project root contains:\n{top_list}\n\n"
            f"{recalled_block}\n\n"
            "Answer strictly with JSON in one of these shapes:\n\n"
            '  {"kind": "plan", "summary": "plan only; no writes"}\n\n'
            '  {"kind": "test", "tests": ["test_module.py"]}\n\n'
            '  {"kind": "inspect", '
            '"summary": "what must be investigated"}\n\n'
            '  {"kind": "code_change", '
            '"files": ["path/to/existing.py", ...], '
            '"summary": "one line describing the exact change"}\n\n'
            '  {"kind": "clarify", '
            '"questions": ["...", "..."]}\n\n'
            '  {"kind": "other", '
            '"note": "the task is unrelated to coding"}\n\n'
            "Rules:\n"
            "- Use inspect when the user asks to inspect, analyze, "
            "locate, identify, explain, review, or determine which "
            "project files are relevant without applying a code change.\n"
            "- Use plan for an implementation plan without applying changes, and test for running existing tests.\n"
            "- A code_change may declare existing Python unittest modules in a tests list. Never weaken tests to make code pass.\n"
            "- If the user explicitly says not to modify anything yet, "
            "use inspect.\n"
            "- Missing file paths are NOT by themselves a reason to "
            "clarify when they can be discovered from the project.\n"
            "- Use clarify only when information required for the task "
            "cannot reasonably be discovered from the project or the "
            "explicit request.\n"
            "- If a code-change task names a file, list it exactly as "
            "the user named it.\n"
            "- Do NOT invent file paths.\n"
            "- If the task is unrelated to coding, use other.\n"
            "Reply with ONLY the JSON. No prose."
        )

        try:
            reply = request_model(caller,
                capability="plan",
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            return {
                "kind": "error",
                "error": f"classify failed: {exc}",
            }

        try:
            value = parse_object(reply)
            if value.get("kind") not in {"inspect", "plan", "test", "code_change", "clarify", "other"}:
                raise ValueError("unknown Coding operation")
            if value.get("kind") == "clarify":
                questions = value.get("questions")
                if not isinstance(questions, list) or not questions or any(not isinstance(q, str) or not q.strip() for q in questions):
                    raise ValueError("clarification requires nonempty questions")
            return value
        except (ValueError, TypeError):
            return {"kind": "error", "error": "model returned an invalid Coding classification"}
