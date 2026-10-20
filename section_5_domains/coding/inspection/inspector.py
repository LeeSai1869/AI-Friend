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
            analysis = self.analyzer.analyze(
                task=task,
                inspected=inspected,
                caller=caller,
            )
        except Exception as exc:
            return {
                "status": "error",
                "error": (
                    "inspection analysis failed: "
                    f"{exc}"
                ),
            }

        return {
            "status": "ok",
            "operation": "no_change",
            "output": analysis,
            "artifacts": [],
            "inspection": {
                "project": project_context.project.to_dict(),
                "files": list(inspected.keys()),
                "writes": 0,
            },
        }
