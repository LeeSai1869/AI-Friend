"""Single Coding-owned facade for the active project."""

from __future__ import annotations

from pathlib import Path

from .history import ProjectHistory
from .memory import ProjectMemory
from .project import CodingProject
from .rules import ProjectRules
from .tree import ProjectTree
from .workspace import CodingWorkspace


class CodingProjectContext:
    def __init__(self):
        self._project = None
        self._workspace = None
        self._tree = None
        self._rules = None
        self._memory = None
        self._history = None

    @property
    def is_open(self) -> bool:
        return self._project is not None

    @property
    def project(self):
        return self._project

    @property
    def workspace(self):
        return self._workspace

    @property
    def tree(self):
        return self._tree

    @property
    def rules(self):
        return self._rules

    @property
    def memory(self):
        return self._memory

    @property
    def history(self):
        return self._history

    def open(self, root: str | Path) -> dict:
        project = CodingProject.open(root)
        workspace = CodingWorkspace(project)

        self._project = project
        self._workspace = workspace
        self._tree = ProjectTree(workspace)
        self._rules = ProjectRules(workspace)
        self._memory = ProjectMemory(workspace)
        self._history = ProjectHistory(workspace)

        return self.describe()

    def close(self) -> None:
        self._project = None
        self._workspace = None
        self._tree = None
        self._rules = None
        self._memory = None
        self._history = None

    def require_open(self) -> None:
        if not self.is_open:
            raise RuntimeError("no Coding project is open")

    def describe(self) -> dict:
        self.require_open()

        return {
            "project": self.project.to_dict(),
            "rules": self.rules.load(),
            "project_memory": self.memory.read(),
        }

    def list_tree(self, relative: str = "") -> list[dict]:
        self.require_open()
        return self.tree.list(relative)
