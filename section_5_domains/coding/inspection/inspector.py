from __future__ import annotations

from .analyzer import InspectionAnalyzer
from .selector import RelevantFileSelector


class CodingInspector:
    """Inspect the already-open Coding Project using its owned context."""

    def __init__(self):
        self.selector = RelevantFileSelector()
        self.analyzer = InspectionAnalyzer()

    def inspect(
        self,
        *,
        task: str,
        project_context,
        broker,
        caller,
    ):
        project_context.require_open()

        project_files = project_context.tree.files()

        if not project_files:
            return {
                "status": "error",
                "error": (
                    "The open Coding Project contains no readable "
                    "project files."
                ),
            }

        try:
            project_memory = project_context.memory.read()
        except Exception:
            project_memory = {}

        try:
            project_history = project_context.history.read()
        except Exception:
            project_history = []

        try:
            project_rules = project_context.rules.load()
        except Exception:
            project_rules = {}

        try:
            selected = self.selector.select(
                task=task,
                project_files=project_files,
                caller=caller,
                project_memory=project_memory,
                project_history=project_history,
                project_rules=project_rules,
            )
        except Exception as exc:
            return {
                "status": "error",
                "error": (
                    "inspection file selection failed: "
                    f"{exc}"
                ),
            }

        if not selected:
            return {
                "status": "needs_answers",
                "questions": [
                    {
                        "attribute": "inspection_target",
                        "question": (
                            "I inspected the current project's structure "
                            "and orientation but could not reliably identify "
                            "which existing files contain the relevant "
                            "implementation. Can you narrow the feature or "
                            "area I should investigate?"
                        ),
                        "options": [],
                        "default": None,
                    }
                ],
                "output": (
                    "I inspected the current project's structure but need "
                    "a narrower target before I can reliably identify the "
                    "relevant files."
                ),
            }

        inspected = self.analyzer.read_selected(
            selected_files=selected,
            broker=broker,
        )

        if not inspected:
            return {
                "status": "error",
                "error": (
                    "Relevant files were identified but could not be "
                    "read through the guarded Coding workspace."
                ),
            }

        try:
            assessment = self.analyzer.assess(
                task=task,
                inspected=inspected,
                caller=caller,
            )
            remaining = (
                self.analyzer.MAX_TOTAL_CHARACTERS
                - sum(len(content) for content in inspected.values())
            )
            additional = []
            if (
                assessment["evidence_sufficient"] is False
                and assessment["missing_context"].strip()
                and remaining > 0
            ):
                additional = self.selector.select(
                    task=task,
                    project_files=project_files,
                    caller=caller,
                    project_memory=project_memory,
                    project_history=project_history,
                    project_rules=project_rules,
                    excluded_files=list(inspected),
                    followup_context=assessment["missing_context"],
                )
            truncated_files = list(self.analyzer.last_truncated_files)
            unreadable_files = dict(self.analyzer.last_read_errors)
            followup = {}
            if additional and remaining > 0:
                followup = self.analyzer.read_selected(
                    selected_files=additional,
                    broker=broker,
                    remaining_characters=remaining,
                )
                inspected.update(followup)
                truncated_files.extend(self.analyzer.last_truncated_files)
                unreadable_files.update(self.analyzer.last_read_errors)
            if followup:
                analysis = self.analyzer.analyze(
                    task=task,
                    inspected=inspected,
                    caller=caller,
                )
            else:
                analysis = str(assessment["answer"]).strip()
        except Exception as exc:
            return {
                "status": "error",
                "error": (
                    "inspection analysis failed: "
                    f"{exc}"
                ),
            }

        indexed_limit = self.selector.MAX_INVENTORY_FILES
        coverage = {
            "project_files_indexed": len(project_files),
            "inventory_limit_reached": len(project_files) >= indexed_limit,
            "files_inspected": list(inspected),
            "additional_batch_read": bool(followup),
            "truncated_files": list(dict.fromkeys(truncated_files)),
            "unreadable_files": unreadable_files,
            "characters_inspected": sum(
                len(content) for content in inspected.values()
            ),
            "context_character_limit": self.analyzer.MAX_TOTAL_CHARACTERS,
        }
        coverage_note = (
            f"Inspection coverage: read {len(inspected)} file(s) from "
            f"{len(project_files)} indexed; "
            f"{'one additional batch was read' if coverage['additional_batch_read'] else 'no additional batch was needed'}."
        )
        if coverage["truncated_files"]:
            coverage_note += (
                " Truncated or not read within the context limit: "
                + ", ".join(coverage["truncated_files"])
                + "."
            )
        if coverage["unreadable_files"]:
            coverage_note += (
                " Unreadable files: "
                + ", ".join(coverage["unreadable_files"])
                + "."
            )
        if coverage["inventory_limit_reached"]:
            coverage_note += (
                f" The project inventory reached its {indexed_limit}-file limit."
            )

        return {
            "status": "ok",
            "operation": "no_change",
            "output": f"{analysis}\n\n{coverage_note}",
            "artifacts": [],
            "inspection": {
                "project": project_context.project.to_dict(),
                "files": list(inspected.keys()),
                "writes": 0,
                "coverage": coverage,
            },
        }
