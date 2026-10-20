"""Coding domain engine.

Contract:
  - The domain reads, plans, writes, tests, verifies.
  - If the request does NOT describe a concrete code change,
    the domain DOES NOT invent files. It returns questions.
  - It NEVER writes a file that was not named in the request
    or identified in the plan as an existing file.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from mind.organ import Organ
from .project_context import CodingProjectContext


def _assess_coding_result(applied, test_result, syntax_check_required=False):
    """Require explicit evidence for writes and required syntax checks."""
    if not isinstance(applied, list) or not applied:
        return {"ok": False, "reason": "no files were written"}

    if any(not isinstance(item, dict) for item in applied):
        return {"ok": False, "reason": "malformed file-write result"}

    failed = [item for item in applied if item.get("ok") is not True]
    if failed:
        paths = ", ".join(str(item.get("path", "?")) for item in failed)
        return {"ok": False, "reason": f"file write failed: {paths}"}

    if syntax_check_required:
        if not isinstance(test_result, dict):
            return {
                "ok": False,
                "reason": "Python syntax check returned no valid result",
            }

        if test_result.get("ok") is not True:
            return {"ok": False, "reason": "Python syntax check failed"}

        data = test_result.get("data")
        if not isinstance(data, dict) or data.get("returncode") != 0:
            return {
                "ok": False,
                "reason": "Python syntax check result lacked a successful exit code",
            }

        return {
            "ok": True,
            "reason": "file writes and Python syntax check succeeded",
        }

    if test_result is not None:
        if not isinstance(test_result, dict) or test_result.get("ok") is not True:
            return {"ok": False, "reason": "provided test result was invalid or failed"}

    return {
        "ok": True,
        "reason": "file writes succeeded; no Python syntax check was applicable",
    }


class CodingOrgan(Organ):
    name = "coding"
    kind = "domain"
    scope = "outside_guards"
    capabilities = [
        "inspect_code", "plan_code", "write_code",
        "test_code", "debug_code", "verify_code",
    ]
    keywords = [
        "code", "python", "javascript", "bug", "debug", "function", "class",
        "script", "test", "file", "module", "refactor", "error", "traceback",
        "compile", "implement", "fix", "add", "endpoint", "route", "server",
    ]

    def __init__(self):
        self.root = Path.cwd()
        self.project_context = CodingProjectContext()

    def verify(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Verify CodingOrgan success claims using explicit execution evidence."""
        if not isinstance(response, dict):
            return {"ok": False, "reason": "coding response is not a dictionary"}

        # Errors and clarification requests are not claims of successful coding.
        if response.get("status") != "ok":
            return {"ok": True, "reason": "response does not claim coding success"}

        operation = response.get("operation")
        artifacts = response.get("artifacts")

        if operation == "no_change":
            if artifacts == []:
                return {"ok": True, "reason": "no-change response confirms no files were written"}
            return {"ok": False, "reason": "no-change response must have an empty artifact list"}

        if operation != "code_change":
            return {"ok": False, "reason": "successful response lacks a recognized operation"}

        if (
            not isinstance(artifacts, list)
            or not artifacts
            or any(not isinstance(path, str) or not path.strip() for path in artifacts)
        ):
            return {"ok": False, "reason": "successful code change lacks valid artifact paths"}

        evidence = response.get("verification")
        if not isinstance(evidence, dict) or evidence.get("ok") is not True:
            return {"ok": False, "reason": "successful code change lacks passing verification evidence"}

        if not isinstance(evidence.get("reason"), str) or not evidence["reason"].strip():
            return {"ok": False, "reason": "verification evidence lacks a reason"}

        checks = evidence.get("checks")
        if not isinstance(checks, dict) or checks.get("file_writes") is not True:
            return {"ok": False, "reason": "file-write verification did not pass"}

        has_python = any(path.lower().endswith(".py") for path in artifacts)
        expected_syntax = "passed" if has_python else "not_applicable"

        if checks.get("python_syntax") != expected_syntax:
            return {
                "ok": False,
                "reason": f"Python syntax evidence must be {expected_syntax}",
            }

        return {"ok": True, "reason": "coding evidence passed validation"}

    def can_handle(self, request: Dict[str, Any]) -> bool:
        text = (request.get("text") or "").lower()
        return any(k in text for k in self.keywords)

    def open_project(self, root):
        """Open a Coding-owned project without invoking cognition."""
        context = self.project_context.open(root)
        return context.describe()

    def close_project(self):
        """Close the current Coding-owned project."""
        self.project_context.close()
        return {"open": False}

    def describe_project(self):
        return self.project_context.describe()

    def list_project_tree(self, path=""):
        self.project_context.require_open()
        return self.project_context.list_tree(path)

    def project_broker(self, broker):
        """Scope an already trusted Coding broker to the active project."""
        self.project_context.require_open()
        return broker.with_workspace(
            self.project_context.workspace.root
        )

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        task = (request.get("text") or "").strip()
        broker = request.get("broker")

        if (
            broker is not None
            and self.project_context.describe().get("open")
        ):
            broker = self.project_broker(broker)
        caller = request.get("caller")

        if broker is None or caller is None:
            return {"status": "error", "error": "coding domain requires broker and caller"}

        # ------------------------------------------------------------------
        # 1. Inspect: read the top-level layout so the model knows what exists.
        # ------------------------------------------------------------------
        top = broker.call("list_files", {"path": ""})
        top_entries = (top.get("data") or {}).get("entries", [])
        top_list = "\n".join(f"  {e['path']}" for e in top_entries)

        # ------------------------------------------------------------------
        # 1b. Recall: what does memory already know about this task?
        # ------------------------------------------------------------------
        memory_bridge = request.get("memory")
        recalled_successes: List[Dict[str, Any]] = []
        recalled_failures: List[Dict[str, Any]] = []
        recalled_block = ""

        if memory_bridge is not None:
            try:
                recalled_successes = memory_bridge.recall_tested(
                    query=task, domain="Cod", limit=5
                )
                recalled_failures = memory_bridge.recall_rejections(
                    query=task, domain="Cod", limit=5
                )

                lines = []
                if recalled_successes:
                    lines.append("Previously successful solutions:")
                    for m in recalled_successes:
                        lines.append(
                            f"  [{m['state']}] {m['title']} "
                            f"(score={m['score']:.2f}, "
                            f"success={m['success_count']}, "
                            f"fail={m['failure_count']})"
                        )
                if recalled_failures:
                    lines.append("Previously rejected approaches (do not repeat):")
                    for m in recalled_failures:
                        lines.append(
                            f"  {m['title']} - {m.get('content', '')[:200]}"
                        )
                if lines:
                    recalled_block = "\n".join(lines)
                    print(f"[coding] memory recall: "
                          f"{len(recalled_successes)} successes, "
                          f"{len(recalled_failures)} failures")
            except Exception as e:
                print(f"[coding] memory recall failed: {e}")

        # ------------------------------------------------------------------
        # 2. Classify: is this a concrete code change?
        # ------------------------------------------------------------------
        classify_prompt = (
            f"Task: {task}\n\n"
            f"Project root contains:\n{top_list}\n\n"
            f"{recalled_block}\n\n"
            "Answer strictly with JSON in one of these shapes:\n\n"
            '  {"kind": "code_change", "files": ["path/to/existing.py", ...], '
            '"summary": "one line describing the exact change"}\n\n'
            '  {"kind": "clarify", "questions": ["...", "..."]}\n\n'
            '  {"kind": "other", "note": "the task is not a code change"}\n\n'
            "Rules:\n"
            "- If the task names a file, list it EXACTLY as the user named it.\n"
            "- Do NOT add folders to a file name. If the user says 'utils.py',\n"
            "  use 'utils.py'. Not 'section_0_app/utils.py'. Not any other path.\n"
            "- If no file is named and no file is implied, use clarify.\n"
            "- If the task is not a code change at all, use other.\n"
            "- Do NOT invent file paths.\n"
            "Reply with ONLY the JSON. No prose."
        )

        try:
            classify_reply = caller.call(
                "coder_model",
                messages=[{"role": "user", "content": classify_prompt}],
            )
        except Exception as e:
            return {"status": "error", "error": f"classify failed: {e}"}

        import json as _json
        import re as _re
        classified: Dict[str, Any] = {}
        try:
            classified = _json.loads(classify_reply)
        except Exception:
            m = _re.search(r"\{.*\}", classify_reply, _re.DOTALL)
            if m:
                try:
                    classified = _json.loads(m.group(0))
                except Exception:
                    classified = {}

        kind = classified.get("kind", "")

        # ------------------------------------------------------------------
        # 3. Branch by classification.
        # ------------------------------------------------------------------
        if kind == "clarify":
            questions = classified.get("questions") or [
                "What exactly should I change, and in which existing file?"
            ]
            return {
                "status": "needs_answers",
                "questions": [{"attribute": "clarification", "options": [], "default": ""}],
                "output": "I need clarification before changing anything:\n  - " +
                          "\n  - ".join(str(q) for q in questions),
            }

        if kind == "other" or kind == "":
            return {
                "status": "ok",
                "operation": "no_change",
                "output": (
                    "This does not look like a concrete code change I can perform.\n"
                    "No files were written.\n"
                    f"Task: {task}"
                ),
                "artifacts": [],
            }

        # kind == "code_change"
        files_to_change: List[str] = list(classified.get("files") or [])
        summary: str = classified.get("summary", "")

        if not files_to_change:
            return {
                "status": "needs_answers",
                "questions": [{"attribute": "target_file", "options": [], "default": ""}],
                "output": "Which existing file should I change?",
            }

        # ------------------------------------------------------------------
        # 4. Read the named files.
        # ------------------------------------------------------------------
        contents = {}
        new_files = []
        for f in files_to_change[:10]:
            r = broker.call("read_file", {"path": f})
            if r.get("ok"):
                contents[f] = r["data"]["content"]
            else:
                # If the file does not exist but the user named it, treat it
                # as a new file to create.
                new_files.append(f)

        if not contents and not new_files:
            return {
                "status": "needs_answers",
                "questions": [{"attribute": "target_file", "options": [], "default": ""}],
                "output": "Which file should I change?",
            }

        # The list of files we are allowed to write:
        allowed_files = list(contents.keys()) + new_files

        # ------------------------------------------------------------------
        # 5. Ask for the change, only for those files.
        # ------------------------------------------------------------------
        files_block = "\n".join(
            f"--- {k} ---\n{v[:4000]}" for k, v in contents.items()
        )
        new_files_block = "\n".join(f"--- NEW: {k} ---" for k in new_files)
        change_prompt = (
            f"Task: {task}\n\n"
            f"Change summary: {summary}\n\n"
            f"{recalled_block}\n\n"
            f"Existing files:\n{files_block}\n\n"
            "Write the change. Reply with a JSON object:\n"
            '{"writes": [{"path": "file.py", "content": "full new content"}]}\n'
            f"You may ONLY write these files: {allowed_files}\n"
            "Do NOT invent any other path."
        )
        try:
            change_reply = caller.call(
                "coder_model",
                messages=[{"role": "user", "content": change_prompt}],
            )
        except Exception as e:
            return {"status": "error", "error": f"change call failed: {e}"}

        writes: List[Dict[str, str]] = []
        try:
            obj = _json.loads(change_reply)
            if isinstance(obj, dict) and isinstance(obj.get("writes"), list):
                writes = obj["writes"]
        except Exception:
            m = _re.search(r"\{.*\}", change_reply, _re.DOTALL)
            if m:
                try:
                    obj = _json.loads(m.group(0))
                    if isinstance(obj, dict) and isinstance(obj.get("writes"), list):
                        writes = obj["writes"]
                except Exception:
                    pass

        # Reject any write to a file we did not name.
        allowed = set(allowed_files)
        writes = [w for w in writes if w.get("path") in allowed]

        if not writes:
            return {
                "status": "needs_answers",
                "questions": [{"attribute": "target_file", "options": [], "default": ""}],
                "output": (
                    "The model did not produce a change confined to the named files.\n"
                    f"Named: {list(allowed)}"
                ),
            }

        # ------------------------------------------------------------------
        # 6. Apply.
        # ------------------------------------------------------------------
        applied = []
        for w in writes:
            r = broker.call("write_file", {"path": w["path"], "content": w.get("content", "")})
            applied.append({"path": w["path"], "ok": r.get("ok"), "error": r.get("error")})

        # ------------------------------------------------------------------
        # 7. Test (only the files we wrote).
        # ------------------------------------------------------------------
        test_result = None
        py_paths = [w["path"] for w in writes if w["path"].endswith(".py")]
        if py_paths:
            test_result = broker.call("run_python_compile", {
                "paths": py_paths,
            })

        # 7b. Submit coding results for Central Mind review; do not write memory directly.
        memory_bridge = request.get("memory")
        if memory_bridge is not None and applied:
            try:
                assessment = _assess_coding_result(
                    applied, test_result, syntax_check_required=bool(py_paths)
                )
                files_changed = ", ".join(a["path"] for a in applied)
                memory_bridge.propose_knowledge(
                    domain="Cod",
                    title=f"{summary or task[:80]}",
                    content=(
                        f"Changed: {files_changed}\n"
                        f"Task: {task}\n"
                        f"Summary: {summary}\n"
                        f"Verification: {assessment['reason']}"
                    ),
                    originator=[{"type": "mind", "name": "central"}],
                    tags=["coding", "solution"],
                    kind="observation",
                    requested_class="raw",
                    source_refs=[a["path"] for a in applied],
                    source={
                        "source_type": "coding_run",
                        "changed_files": [a["path"] for a in applied],
                    },
                    evidence={
                        "assessment": assessment,
                        "syntax_check_required": bool(py_paths),
                        "syntax_check_result": str(test_result),
                        "functional_correctness_established": False,
                    },
                    derivation_note=(
                        "Coding result submitted for Central Mind review. "
                        "A successful syntax check alone does not establish functional correctness."
                    ),
                )
            except Exception as e:
                print(f"[coding] memory proposal failed: {e}")

        # ------------------------------------------------------------------
        # 8. Summary.
        # ------------------------------------------------------------------
        lines = [f"[coding] {task}", ""]
        lines.append(f"Summary: {summary}")
        lines.append("")
        lines.append(f"Files written ({len(applied)}):")
        for a in applied:
            status = "OK" if a["ok"] else f"FAILED: {a['error']}"
            lines.append(f"  {a['path']} - {status}")

        if test_result is not None:
            lines.append("")
            lines.append(f"Test: {'PASSED' if test_result.get('ok') else 'FAILED'}")
            out = (test_result.get("data") or {}).get("stdout", "")
            err = (test_result.get("data") or {}).get("stderr", "")
            if out:
                lines.append(f"  stdout: {out[:400]}")
            if err:
                lines.append(f"  stderr: {err[:400]}")

        assessment = _assess_coding_result(applied, test_result, syntax_check_required=bool(py_paths))
        lines.append("")
        lines.append(f"Verification: {assessment['reason']}")

        syntax_state = "not_applicable"
        if py_paths:
            syntax_state = (
                "passed"
                if (
                    isinstance(test_result, dict)
                    and test_result.get("ok") is True
                    and isinstance(test_result.get("data"), dict)
                    and test_result["data"].get("returncode") == 0
                )
                else "failed"
            )

        file_writes_ok = (
            isinstance(applied, list)
            and bool(applied)
            and all(
                isinstance(item, dict) and item.get("ok") is True
                for item in applied
            )
        )

        return {
            "status": "ok" if assessment["ok"] else "error",
            "operation": "code_change",
            "output": "\\n".join(lines),
            "artifacts": [a["path"] for a in applied],
            "verification": {
                "ok": assessment["ok"],
                "reason": assessment["reason"],
                "checks": {
                    "file_writes": file_writes_ok,
                    "python_syntax": syntax_state,
                },
            },
            **({} if assessment["ok"] else {"error": assessment["reason"]}),
        }


ORGAN = CodingOrgan()
