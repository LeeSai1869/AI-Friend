"""Read-only planning and test operations owned by Coding, not by the kernel."""
from __future__ import annotations

import json
from pathlib import PurePosixPath

from .cognition import resource_question
from .planner import Planner
from .tester import Tester


def selected_capability(plan):
    if not isinstance(plan, dict):
        return ''
    if plan.get('selected_capability'):
        return str(plan['selected_capability'])
    steps = [step for step in plan.get('steps', []) if isinstance(step, dict)
             and step.get('kind') == 'domain' and step.get('component') in {'coder', 'coding'}]
    return str(steps[0].get('capability') or '') if len(steps) == 1 else ''


def python_tests(inventory):
    return [path for path in inventory if path.endswith('.py')
            and (PurePosixPath(path).name.startswith('test_') or PurePosixPath(path).name.endswith('_test.py'))]


class CodingOperations:
    def plan(self, *, task, caller, broker, context, inspector, recalled):
        context.require_open()
        files = context.tree.files()
        selected = inspector.selector.select(task=task, project_files=files, caller=caller,
                    project_memory=context.memory.read(), project_history=context.history.read(),
                    project_rules=context.rules.load())
        if not selected and files:
            return resource_question('which project files should the implementation plan address?')
        inspected = inspector.analyzer.read_selected(selected_files=selected, broker=broker)
        output = Planner().plan(task=task, caller=caller, evidence=json.dumps(inspected), recalled=recalled)
        return {'status': 'ok', 'operation': 'no_change', 'artifacts': [], 'output': output,
                'plan': {'files_inspected': list(inspected), 'writes': False}}

    def test(self, *, broker, inventory, paths=None):
        targets = list(paths) if paths else python_tests(inventory)
        if not targets:
            return resource_question('no Python unittest modules were found; provide behavioral tests')
        sources = list(inventory)
        result = Tester().run(broker=broker, paths=targets, sources=sources)
        passed = Tester.passed(result)
        data = result.get('data') or {}
        if not data.get('tests_run'):
            return {**resource_question(result.get('error') or 'functional test runner is unavailable'),
                    'functional_tests': result}
        return {'status': 'ok' if passed else 'error', 'operation': 'test_run', 'artifacts': [],
                'output': f"Functional tests: {data['tests_run']} run, {data.get('passed', 0)} passed, "
                          f"{data.get('failures', 0)} failed, {data.get('errors', 0)} errors, "
                          f"{data.get('skipped', 0)} skipped.\n{data.get('output', '')}",
                'functional_tests': result,
                **({} if passed else {'error': 'functional tests failed'})}
