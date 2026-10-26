"""Coding-owned candidate/test/repair/apply cycle. No raw model or filesystem access."""
from __future__ import annotations

import json
from .cognition import CodingCycle, resource_question
from .tester import Tester


class CodingExecution:
    MAX_REPAIRS = 2

    def __init__(self):
        self.cycle = CodingCycle()
        self.tester = Tester()

    def run(self, *, caller, broker, prompt, allowed_files, tests=(), sources=()):
        attempts = []
        functional = None
        runner_unavailable = None
        snapshot = list(dict.fromkeys([*sources, *allowed_files]))
        for revision in range(self.MAX_REPAIRS + 1):
            writes, candidate_attempts, blocked = self.cycle.generate(
                caller=caller, prompt=prompt, allowed_files=set(allowed_files), broker=broker,
                capability='debug' if revision else 'write',
            )
            attempts.extend({**item, 'revision': revision} for item in candidate_attempts)
            if blocked is not None:
                return {**blocked, 'attempts': attempts}
            if not tests:
                break
            functional = self.tester.run(
                broker=broker, paths=tests, sources=snapshot,
                overrides={item['path']: item['content'] for item in writes},
            )
            attempts.append({'revision': revision, 'stage': 'candidate_tests', 'result': functional})
            if self.tester.passed(functional):
                break
            if self.tester.unavailable(functional):
                # The runner itself is unavailable: apply after the syntax check
                # and report honestly that functional tests did not run.
                runner_unavailable = functional.get('error') or 'functional test runner unavailable'
                functional = None
                break
            data = functional.get('data') or {}
            if not data.get('tests_run'):
                return {**resource_question(functional.get('error') or 'functional test execution is unavailable'),
                        'attempts': attempts, 'functional_tests': functional}
            if revision == self.MAX_REPAIRS:
                return {'status': 'error', 'error': 'functional tests failed after the repair budget',
                        'output': 'No candidate was applied: functional tests still fail.',
                        'artifacts': [], 'attempts': attempts, 'functional_tests': functional}
            prompt += ('\nPrevious candidate (not applied):\n' + json.dumps(writes, ensure_ascii=False) +
                       '\nFunctional test failure evidence:\n' + json.dumps(data, ensure_ascii=False) +
                       '\nRepair the implementation within the original allowed paths. Do not weaken tests.')
        applied = []
        for write in writes:
            result = broker.call('write_file', {'path': write['path'], 'content': write['content']})
            applied.append({'path': write['path'], 'ok': result.get('ok'), 'error': result.get('error')})
            if result.get('ok') is not True:
                # Report partial writes; never continue mutating after denial/failure.
                break
        if not all(item['ok'] is True for item in applied):
            return {'status': 'error', 'error': 'file application failed; earlier writes may remain',
                    'applied': applied, 'attempts': attempts, 'functional_tests': functional,
                    'artifacts': [item['path'] for item in applied if item['ok'] is True]}
        py_paths = [item['path'] for item in writes if item['path'].lower().endswith('.py')]
        syntax = broker.call('run_python_compile', {'paths': py_paths}) if py_paths else None
        if tests and runner_unavailable is None:
            # Re-read the persisted files; candidate-only tests cannot prove the
            # actual write operation produced the intended implementation.
            functional = self.tester.run(broker=broker, paths=tests, sources=snapshot)
        return {'status': 'executed', 'applied': applied, 'writes': writes, 'syntax': syntax,
                'functional_tests': functional, 'attempts': attempts,
                'functional_unavailable': runner_unavailable}
