"""Conventions shared by the Coding domain engines."""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any, Iterable, Optional


def module_under_test(path: str) -> Optional[str]:
    """Return the module a conventionally named test file covers, else None.

    Only test_<name>.py next to <name>.py is conventional here.
    """
    pure = PurePosixPath(str(path or ""))
    name = pure.name
    if not (name.startswith("test_") and name.endswith(".py")) or len(name) <= len("test_.py"):
        return None
    return (pure.parent / name[len("test_"):]).as_posix()


def conventional_test_path(path: str, task: str, known_files: Iterable[str]) -> bool:
    """True when a new test file may be created without the user naming it.

    The task must ask for tests, and the module under test must already exist.
    """
    sibling = module_under_test(path)
    if sibling is None:
        return False
    if "test" not in str(task or "").lower():
        return False
    return sibling in set(known_files or [])


def plan_requirements_block(plan: Any, limit: int = 12, width: int = 300) -> str:
    """Render the planned requirements and constraints for the executing step."""
    if not isinstance(plan, dict):
        return ""
    sections = []
    for title, key in (("Requirements", "requirements"), ("Constraints", "constraints")):
        raw = plan.get(key) or []
        if not isinstance(raw, (list, tuple)):
            continue
        items = [str(item).strip() for item in raw if str(item).strip()]
        if items:
            sections.append(title + ":\n" + "\n".join("- " + item for item in items))
    if not sections:
        return ""
    return "\n\nPlan details (keep exact names, signatures and type annotations):\n" + "\n".join(sections)


def delegated_write_scope(plan):
    """Conservative upper bound from explicit paths in one delegated objective.

    Whole-task requirements remain context. They must not cause this step to
    apply later planned changes. This infers no paths when none are named.
    """
    import re
    if not isinstance(plan,dict):return []
    steps=[row for row in plan.get('steps',[]) if isinstance(row,dict) and row.get('kind')=='domain']
    if len(steps)!=1:return []
    objective=steps[0].get('objective') or ''
    paths=re.findall(r'(?<![\w/])((?:[\w.-]+/)*[\w.-]+\.(?:py|js|ts|jsx|tsx|json|yaml|yml|toml|rs|swift|html|css|txt|md))(?![\w.])',objective)
    if re.search(r'\b(?:create|write|add)\s+(?:(?:unit|behavioral|functional|integration)\s+)?tests?\b',objective,re.I):
        for path in list(paths):
            pure=PurePosixPath(path)
            if pure.suffix=='.py' and not pure.name.startswith('test_') and not pure.name.endswith('_test.py'):
                paths.append(str(pure.with_name('test_'+pure.name)))
    return list(dict.fromkeys(paths))
