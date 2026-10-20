"""Project-specific Coding rules.

These rules belong to the Coding Project. They do not modify the Constitution
and cannot grant authority that Guard does not already permit.
"""

from __future__ import annotations

from ..workspace import CodingWorkspace


DEFAULT_RULE_FILES = (
    ".ai-friend/rules.md",
    "AI_FRIEND.md",
)


class ProjectRules:
    def __init__(self, workspace: CodingWorkspace):
        self.workspace = workspace

    def load(self) -> dict:
        for relative in DEFAULT_RULE_FILES:
            path = self.workspace.resolve(relative)

            if path.is_file():
                return {
                    "source": relative,
                    "content": path.read_text(
                        encoding="utf-8",
                        errors="replace",
                    ),
                }

        return {
            "source": None,
            "content": "",
        }
