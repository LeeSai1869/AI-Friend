from __future__ import annotations

from ..cognition import request_model

import json
import re
from typing import List, Sequence


class RelevantFileSelector:
    """Select real project files relevant to an inspection."""

    MAX_SELECTED_FILES = 12
    MAX_INVENTORY_FILES = 5000
    MAX_ORIENTATION_CHARS = 12000

    def select(
        self,
        *,
        task: str,
        project_files: List[str],
        caller,
        project_memory=None,
        project_history=None,
        project_rules=None,
        excluded_files: Sequence[str] = (),
        followup_context: str = "",
    ) -> List[str]:
        existing_files = list(project_files)[:self.MAX_INVENTORY_FILES]
        inventory = "\n".join(existing_files)
        excluded = set(excluded_files)

        orientation = {
            "project_memory": project_memory or {},
            "recent_project_history": (project_history or [])[-20:],
            "project_rules": project_rules or {},
        }

        orientation_text = json.dumps(
            orientation,
            indent=2,
            ensure_ascii=False,
            default=str,
        )[:self.MAX_ORIENTATION_CHARS]

        prompt = (
            f"Task: {task}\n\n"
            f"Project orientation:\n{orientation_text}\n\n"
            f"Existing project files:\n{inventory}\n\n"
            f"Already inspected; do not select again:\n"
            f"{chr(10).join(sorted(excluded)) or '(none)'}\n\n"
            f"Specific evidence gap to address:\n"
            f"{followup_context or '(initial inspection)'}\n\n"
            "Select the existing files most relevant to answering the task. "
            "Project memory and history are orientation only; the existing "
            "file inventory is authoritative for paths. Do not invent paths "
            "and do not propose modifications. Select at most "
            f"{self.MAX_SELECTED_FILES} files, and return no already-inspected "
            "paths. Return JSON only in this shape: "
            '{"files": ["existing/path", ...], '
            '"reason": "brief reason"}'
        )

        reply = request_model(caller,
            capability="plan",
            messages=[{"role": "user", "content": prompt}],
        )

        selection = {}

        try:
            selection = json.loads(reply)
        except Exception:
            match = re.search(
                r"\{.*\}",
                str(reply),
                re.DOTALL,
            )
            if match:
                try:
                    selection = json.loads(match.group(0))
                except Exception:
                    selection = {}

        existing = set(existing_files)

        return [
            str(path)
            for path in (selection.get("files") or [])
            if str(path) in existing and str(path) not in excluded
        ][:self.MAX_SELECTED_FILES]
