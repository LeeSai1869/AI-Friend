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
from .conventions import conventional_test_path, module_under_test, plan_requirements_block, delegated_write_scope
from .classification import CodingClassifier
from .inspection import CodingInspector
from .recall import CodingRecaller
from .cognition import resource_question
from .experience import CodingExperience
from .execution import CodingExecution
from .operations import CodingOperations, selected_capability, python_tests
from .tester import Tester
from .verifier import Verifier as CodingVerifier
from weakref import WeakKeyDictionary


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
        "application",
    ]
    keywords = [
        "code", "python", "javascript", "bug", "debug", "function", "class",
        "script", "test", "file", "module", "refactor", "error", "traceback",
        "compile", "implement", "fix", "add", "endpoint", "route", "server",
    ]

    def __init__(self, *, session_scoped=True):
        self._session_scoped = session_scoped
        self._sessions = WeakKeyDictionary()
        self.root = Path.cwd()
        self.project_context = CodingProjectContext()
        self.classifier = CodingClassifier()
        self.inspector = CodingInspector()
        self.recaller = CodingRecaller()
        self.execution = CodingExecution()
        self.operations = CodingOperations()
        self.experience = CodingExperience()
        from .intake_examiner import CodingIntakeExaminer
        self.intake_examiner = CodingIntakeExaminer()

    def _for_caller(self, caller):
        if self._session_scoped or caller is None:
            return self
        if caller not in self._sessions:
            domain = CodingOrgan()
            # Knowledge evaluation receives proposals through the generic
            # evaluator contract, not through an individual caller session.
            domain.experience = self.experience
            self._sessions[caller] = domain
        return self._sessions[caller]

    def handle_intake_processing(self, request):
        return self.intake_examiner.examine(request["raw_source"], request.get("existing_knowledge", []))

    def evaluate_knowledge(self, proposal):
        if (proposal.get("source") or {}).get("intake_examiner_version"):
            return self.intake_examiner.evaluate(proposal)
        return self.experience.evaluate(proposal)

    def verify(self, response: Dict[str, Any]) -> Dict[str, Any]:
        return CodingVerifier().verify(response)

    def can_handle(self, request: Dict[str, Any]) -> bool:
        text = (request.get("text") or "").lower()
        return any(k in text for k in self.keywords)

    def open_project(self, root):
        """Open a Coding-owned project without invoking cognition."""
        return self.project_context.open(root)

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

    def handle_consultation(
        self,
        request: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Return bounded Coding-owned evidence without executing the task."""
        domain = self._for_caller(request.get("caller"))
        if domain is not self:
            return domain.handle_consultation(request)

        consultation = request.get("consultation") or {}
        if not isinstance(consultation, dict):
            return {
                "status": "error",
                "error": "consultation payload must be a mapping",
            }

        capability = str(
            consultation.get("capability")
            or request.get("evidence_capability")
            or ""
        ).strip()

        if capability != "project_context":
            return {
                "status": "error",
                "error": (
                    "unsupported Coding evidence capability: "
                    + repr(capability)
                ),
            }

        if not self.project_context.is_open:
            return {
                "status": "ok",
                "evidence": {
                    "capability": "project_context",
                    "project_open": False,
                    "project": None,
                    "top_level": [],
                },
            }

        try:
            top_level = self.project_context.list_tree("")
        except Exception as exc:
            return {
                "status": "error",
                "error": (
                    "could not read Coding project structure: "
                    + str(exc)
                ),
            }

        return {
            "status": "ok",
            "evidence": {
                "capability": "project_context",
                "project_open": True,
                "project": self.project_context.project.to_dict(),
                "top_level": top_level,
                "file_count": len(self.project_context.tree.files()),
                "file_count_scope": "Files visible in the Coding project inventory; project exclusions apply",
            },
        }

    def handle_application(
        self,
        request: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle non-cognitive Coding application operations.

        Operation names and project semantics are private to Coding.
        Central Mind supplies only trusted shared resources.
        """
        domain = self._for_caller(request.get("caller"))
        if domain is not self:
            return domain.handle_application(request)
        operation = str(request.get("operation") or "").strip()
        payload = request.get("payload") or {}

        if not isinstance(payload, dict):
            return {
                "status": "error",
                "error": "application payload must be a mapping",
            }

        if operation == "open_project":
            root = str(payload.get("root") or "").strip()
            if not root:
                return {
                    "status": "error",
                    "error": "project root is required",
                }

            return {
                "status": "ok",
                "result": self.open_project(root),
            }

        if operation == "close_project":
            return {
                "status": "ok",
                "result": self.close_project(),
            }

        if operation == "project_status":
            if not self.project_context.is_open:
                return {
                    "status": "ok",
                    "result": {"open": False},
                }

            result = self.describe_project()
            result["open"] = True

            return {
                "status": "ok",
                "result": result,
            }

        if operation == "run_tests":
            self.project_context.require_open()
            broker = request.get("broker")
            if broker is None:
                return {"status": "error", "error": "Coding application requires broker"}
            response = self.operations.test(
                broker=self.project_broker(broker),
                inventory=self.project_context.tree.files(),
            )
            # The application request was handled; the nested status retains
            # test failure or missing-resource outcomes without hiding output.
            return {"status": "ok", "result": response}

        if operation == "list_files":
            path = str(payload.get("path") or "")
            return {
                "status": "ok",
                "result": {
                    "path": path,
                    "files": self.list_project_tree(path),
                },
            }

        if operation == "read_file":
            path = str(payload.get("path") or "").strip()
            if not path:
                return {
                    "status": "error",
                    "error": "path is required",
                }

            broker = request.get("broker")
            if broker is None:
                return {
                    "status": "error",
                    "error": "Coding application requires broker",
                }

            try:
                scoped = self.project_broker(broker)
                tool_result = scoped.call(
                    "read_file",
                    {"path": path},
                )
            except Exception as exc:
                return {
                    "status": "error",
                    "error": str(exc),
                }

            if not tool_result.get("ok"):
                return {
                    "status": "error",
                    "error": (
                        tool_result.get("error")
                        or "file read failed"
                    ),
                }

            data = tool_result.get("data") or {}

            return {
                "status": "ok",
                "result": {
                    "path": path,
                    "content": data.get("content", ""),
                    "size": data.get("size"),
                },
            }

        return {
            "status": "error",
            "error": (
                "unsupported Coding application operation: "
                + repr(operation)
            ),
        }

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        domain = self._for_caller(request.get("caller"))
        if domain is not self:
            return domain.handle(request)
        if request.get("task_contract") is not None:
            from mind.task_contract import validate_task_contract
            try:
                validate_task_contract(request["task_contract"])
            except ValueError as exc:
                return {"status": "error", "error": str(exc), "artifacts": []}
        task = (request.get("text") or "").strip()
        task += plan_requirements_block(request.get("cognitive_plan"))
        step_scope = (delegated_write_scope(request.get("cognitive_plan"))
                      if selected_capability(request.get("cognitive_plan")) == "write_code" else [])
        if step_scope:
            task += "\nCurrent delegated step may write only these named targets: " + ", ".join(step_scope)
            task += ". Original objective/global requirements are context; do not implement later steps in this operation."
        answers = request.get("answers")
        if isinstance(answers, dict) and any(value for value in answers.values()):
            import json
            task += "\nUser clarifications: " + json.dumps(answers, ensure_ascii=False, default=str)
        broker = request.get("broker")

        if (
            broker is not None
            and self.project_context.is_open
        ):
            broker = self.project_broker(broker)
        caller = request.get("caller")

        if broker is None or caller is None:
            return {"status": "error", "error": "coding domain requires broker and caller"}

        # Recall Coding experience through the supplied Memory bridge.
        recalled_block = self.recaller.recall(
            task=task,
            memory_bridge=request.get("memory"),
        )

        capability = selected_capability(request.get("cognitive_plan"))
        if capability in {"plan_code", "test_code", "verify_code"}:
            if not self.project_context.is_open:
                return resource_question("open a Coding Project before planning or running tests")
            try:
                if capability == "plan_code":
                    return self.operations.plan(task=task, caller=caller, broker=broker,
                        context=self.project_context, inspector=self.inspector, recalled=recalled_block)
                return self.operations.test(broker=broker, inventory=self.project_context.tree.files())
            except Exception as exc:
                return resource_question(str(exc))

        # Decide which Coding responsibility owns this request.
        classified = self.classifier.classify(
            task=task,
            broker=broker,
            caller=caller,
            recalled_block=recalled_block,
        )

        # The classifier refines the delegated operation; it cannot silently
        # replace an explicit write assignment with a read-only plan.
        if capability == "write_code" and classified.get("kind") in {"plan", "test", "inspect", "other"}:
            classified = self.classifier.classify(
                task=task + "\nDispatch correction: Central Mind delegated write_code. "
                "Return code_change with the exact requested file paths, or clarify if a material "
                "requirement is genuinely unresolved. Do not substitute a read-only plan.",
                broker=broker, caller=caller, recalled_block=recalled_block,
            )
            if classified.get("kind") not in {"code_change", "clarify", "error"}:
                return {"status": "error", "operation": "no_change", "artifacts": [],
                        "error": "Coding classification did not honor write_code after one correction. No files were written."}

        if (step_scope and classified.get("kind") == "code_change"
                and isinstance(classified.get("files"),list)
                and any(path not in step_scope for path in classified["files"])):
            classified = self.classifier.classify(task=task +
                "\nScope correction: return only this delegated step's targets, not the entire user task. "
                "Return code_change or a material clarification.",broker=broker,caller=caller,recalled_block=recalled_block)
            if (classified.get("kind") not in {"code_change","clarify","error"}
                    or any(path not in step_scope for path in (classified.get("files") or []))):
                return {"status":"error","artifacts":[],"error":"Coding classification exceeded the delegated step's write scope after correction. No files were written."}

        kind = "inspect" if capability == "inspect_code" else classified.get("kind", "")

        if kind == "error":
            return resource_question(classified.get("error") or "coding classification failed")

        if kind in {"plan", "test"}:
            if not self.project_context.is_open:
                return resource_question("open a Coding Project before planning or running tests")
            if kind == "plan":
                return self.operations.plan(task=task, caller=caller, broker=broker,
                    context=self.project_context, inspector=self.inspector, recalled=recalled_block)
            return self.operations.test(broker=broker, inventory=self.project_context.tree.files(),
                                        paths=classified.get("tests"))

        if kind == "inspect":
            if not self.project_context.is_open:
                return {
                    "status": "needs_answers",
                    "questions": [{
                        "attribute": "coding_project",
                        "question": "Which Coding Project should I inspect?",
                        "options": [],
                        "default": None,
                    }],
                    "output": "Open a Coding Project before asking me to inspect its code.",
                }

            return self.inspector.inspect(
                task=task,
                project_context=self.project_context,
                broker=broker,
                caller=caller,
            )

        if kind == "clarify":
            questions = classified.get("questions") or [
                "What exactly should I change, and in which existing file?"
            ]
            return {
                "status": "needs_answers",
                "questions": [
                    {
                        "attribute": f"clarification_{i + 1}",
                        "question": str(q),
                        "options": [],
                        "default": None,
                    }
                    for i, q in enumerate(questions)
                ],
                "output": "I need clarification before changing anything:\n  - " +
                          "\n  - ".join(str(q) for q in questions),
            }

        if kind not in {"other", "code_change", "inspect", "clarify"}:
            return resource_question("model did not identify a valid Coding responsibility")

        if kind == "other":
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
        files_to_change = classified.get("files")
        if not isinstance(files_to_change, list) or any(not isinstance(f, str) or not f.strip() for f in files_to_change):
            return resource_question("a valid list of target files is required")
        files_to_change = list(dict.fromkeys(files_to_change))
        if len(files_to_change) > 10:
            return resource_question("the change exceeds the ten-file operation budget; split the task")
        summary: str = classified.get("summary", "")

        if not files_to_change:
            return {
                "status": "needs_answers",
                "questions": [{
                    "attribute": "target_file",
                    "question": "Which existing file should I change?",
                    "options": [],
                    "default": None,
                }],
                "output": "Which existing file should I change?",
            }

        # ------------------------------------------------------------------
        # 4. Read the named files.
        # ------------------------------------------------------------------
        contents = {}
        new_files = []
        reference = {}
        for f in files_to_change[:10]:
            r = broker.call("read_file", {"path": f})
            if r.get("ok"):
                contents[f] = r["data"]["content"]
            elif str(r.get("error", "")).startswith("not found:"):
                # A missing file is distinct from denied or unreadable content.
                # New paths must have been named explicitly by the user.
                if f not in task and not conventional_test_path(
                    f, task,
                    self.project_context.tree.files() if self.project_context.is_open else [],
                ):
                    return resource_question("confirm the proposed new file path " + f)
                new_files.append(f)
                sibling = module_under_test(f)
                if sibling and sibling not in contents:
                    sibling_read = broker.call("read_file", {"path": sibling})
                    if sibling_read.get("ok"):
                        reference[sibling] = sibling_read["data"]["content"]
            else:
                return {"status": "error", "error": r.get("error") or "file read failed", "artifacts": []}

        if not contents and not new_files:
            return {
                "status": "needs_answers",
                "questions": [{
                    "attribute": "target_file",
                    "question": "Which file should I change?",
                    "options": [],
                    "default": None,
                }],
                "output": "Which file should I change?",
            }

        # The list of files we are allowed to write:
        allowed_files = list(contents.keys()) + new_files

        # ------------------------------------------------------------------
        # 5. Ask for the change, only for those files.
        # ------------------------------------------------------------------
        files_block = "\n".join(
            f"--- {k} ---\n{v}" for k, v in contents.items()
        )
        if len(files_block) > 48000:
            return resource_question("the selected files exceed the full-file context budget; narrow the change")
        new_files_block = "\n".join(f"--- NEW: {k} ---" for k in new_files)
        reference_block = "".join(
            f"Reference file (read-only, do not write it):\n--- {k} ---\n{v[:12000]}\n\n"
            for k, v in reference.items()
        )
        change_prompt = (
            f"Task: {task}\n\n"
            f"Change summary: {summary}\n\n"
            f"{recalled_block}\n\n"
            f"Existing files:\n{files_block}\n\nNew files:\n{new_files_block}\n\n{reference_block}"
            "Write the change. Keep every function name, signature and type annotation exactly as the task states. If you write tests, use the standard unittest module so they need no extra packages. Reply with a JSON object:\n"
            '{"writes": [{"path": "file.py", "content": "full new content"}]}\n'
            f"You may ONLY write these files: {allowed_files}\n"
            "Do NOT invent any other path."
        )
        inventory = self.project_context.tree.files() if self.project_context.is_open else list(contents)
        tests = classified.get("tests") or []
        if not isinstance(tests, list) or any(not isinstance(path, str) for path in tests):
            return resource_question("test targets must be a list of Python module paths")
        if any(path not in inventory and path not in allowed_files for path in tests):
            return resource_question("functional tests must be existing files or explicitly planned artifacts")
        # A model may suggest extra targets, but cannot opt out of the
        # project's existing regression tests by returning an empty list.
        tests = list(dict.fromkeys([*python_tests(inventory), *python_tests(allowed_files), *tests]))
        execution = self.execution.run(caller=caller, broker=broker, prompt=change_prompt,
            allowed_files=allowed_files, tests=tests,
            sources=inventory, acceptance_checks=(request.get("cognitive_plan") or {}).get("acceptance_checks", []))
        if execution.get("status") != "executed":
            return execution
        writes, attempts = execution["writes"], execution["attempts"]
        applied, test_result = execution["applied"], execution["syntax"]
        functional_result = execution["functional_tests"]
        py_paths = [write["path"] for write in writes if write["path"].lower().endswith(".py")]

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
            lines.append(f"Python syntax check: {'PASSED' if test_result.get('ok') else 'FAILED'}")
            if functional_result is None:
                unavailable = execution.get("functional_unavailable")
                written_tests = [a["path"] for a in applied if module_under_test(a["path"])]
                if unavailable:
                    lines.append("Functional tests were not run: " + str(unavailable) + ". Only file writes and Python syntax were checked.")
                elif written_tests:
                    lines.append("Test file(s) written but not executed: " + ", ".join(written_tests) + ". Functional behavior is unverified.")
                else:
                    lines.append("Functional tests have not been run: no test modules were selected.")
            out = (test_result.get("data") or {}).get("stdout", "")
            err = (test_result.get("data") or {}).get("stderr", "")
            if out:
                lines.append(f"  stdout: {out[:400]}")
            if err:
                lines.append(f"  stderr: {err[:400]}")

        assessment = _assess_coding_result(applied, test_result, syntax_check_required=bool(py_paths))
        lines.append("")
        if functional_result is not None:
            data = functional_result.get("data") or {}
            if not Tester.passed(functional_result):
                assessment = {"ok": False, "reason": "persisted functional tests failed"}
            elif assessment["ok"]:
                assessment["reason"] += "; functional tests passed"
            lines.append(f"Functional tests: {data.get('tests_run', 0)} run, {data.get('passed', 0)} passed")
            lines.append(str(data.get("output", "")))
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

        result = {
            "status": "ok" if assessment["ok"] else "error",
            "operation": "code_change",
            "applied": applied,
            "functional_unavailable": execution.get("functional_unavailable"),
            "acceptance": execution.get("acceptance"),
            "output": "\n".join(lines),
            "attempts": attempts,
            "functional_tests": functional_result,
            "provider": (getattr(caller, "last_source", None) or {}).get("name"),
            "artifacts": [a["path"] for a in applied],
            "verification": {
                "ok": assessment["ok"],
                "reason": assessment["reason"],
                "checks": {
                    "file_writes": file_writes_ok,
                    "python_syntax": syntax_state,
                },
            },
            "learning_candidate": {
                "domain": "Cod", "kind": "observation",
                "title": summary or task[:80],
                "content": (
                    f"Task: {task}\nFiles: {', '.join(a['path'] for a in applied)}\n"
                    f"Outcome: {assessment['reason']}\n"
                    f"Functional checks: {functional_result.get('data') if functional_result else 'not run; functional correctness is unverified'}\n"
                    f"Candidate attempts: {attempts}"
                ),
                "tags": ["coding", "bounded_execution", "functional_tests" if functional_result else "syntax_only"],
                "source_refs": [a["path"] for a in applied],
                "source": dict(getattr(caller, "last_source", None) or {}),
                "derivation_note": "Observed Coding execution; preserve failures and the limited verification scope.",
            },
            **({} if assessment["ok"] else {"error": assessment["reason"]}),
        }
        from .learning import verified_example
        candidate = result.pop("learning_candidate")
        learned_content = verified_example(task=task, task_contract=request.get("task_contract"),
            writes=writes, assessment=assessment, functional_result=functional_result)
        if learned_content is not None:
            candidate["content"] = learned_content
            candidate["source"].setdefault("type", "mind")
            import hashlib, json
            example = json.loads(learned_content)
            identity = {"objective":(request.get("task_contract") or {}).get("original_objective") or task,
                        "files":[{"path":item["path"],"sha256":item["sha256"]} for item in example["files"]],
                        "requirements":(request.get("task_contract") or {}).get("requirements",[]),
                        "constraints":(request.get("task_contract") or {}).get("constraints",[])}
            candidate["source"]["verified_example_fingerprint"] = hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
            candidate["tags"] = ["coding", "verified_example", "selected_behavioral_tests"]
            candidate["derivation_note"] = "Behaviorally checked example with source snapshot and verification scope; applicability must be reassessed."
            result["learning_candidate"] = candidate
            self.experience.remember(candidate, assessment, functional_result)
        else:
            result["learning_disposition"] = {"status":"not_proposed",
                "reason":"No compact behaviorally verified example: syntax-only runs, failed checks and oversized examples remain operational evidence."}
        return result


ORGAN = CodingOrgan(session_scoped=False)
