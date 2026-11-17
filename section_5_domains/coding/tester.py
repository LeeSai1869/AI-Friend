"""Coding's test coordinator. Execution belongs exclusively to guarded tools."""
from __future__ import annotations

import re


class Tester:
    def run(self, *, broker, paths, sources, overrides=None):
        if not paths:
            return {'ok': False, 'data': None, 'error': 'no functional test modules were selected'}
        return broker.call('run_python_tests', {
            'paths': list(paths), 'sources': list(sources),
            'overrides': dict(overrides or {}),
        })

    @staticmethod
    def passed(result):
        data = (result or {}).get('data') or {}
        return (result.get('ok') is True and data.get('returncode') == 0
                and type(data.get('tests_run')) is int and data['tests_run'] > 0
                and type(data.get('passed')) is int and data['passed'] > 0
                and data.get('failures') == 0 and data.get('errors') == 0)

    @staticmethod
    def failure_details(result):
        data = (result or {}).get('data') or {}
        output = str(data.get('output') or '')
        lines = output.splitlines()
        markers = []

        for index, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('FAILED '):
                summary = stripped[len('FAILED '):]
                name, separator, assertion = summary.partition(' - ')
                markers.append((index, name.strip(), assertion.strip() if separator else ''))
            elif stripped.startswith(('FAIL:', 'ERROR:')):
                name = stripped.split(':', 1)[1].strip()
                markers.append((index, name, ''))

        details = []
        for marker_index, (line_index, name, summary_assertion) in enumerate(markers):
            next_index = markers[marker_index + 1][0] if marker_index + 1 < len(markers) else len(lines)
            block = lines[line_index + 1:next_index]
            assertion = summary_assertion
            if not assertion:
                for line in block:
                    value = line.strip()
                    value = re.sub(r'^[E ]+\s?', '', value)
                    if 'AssertionError:' in value:
                        assertion = value[value.index('AssertionError:') + len('AssertionError:'):].strip()
                    elif value.startswith(('assert ', 'assertion failed')):
                        assertion = value
                    if assertion:
                        break
            details.append({
                'name': name or 'unknown test',
                'assertion': assertion or 'test runner reported a failure without an assertion message',
            })

        if not details and (data.get('failures') or data.get('errors')):
            details.append({
                'name': 'unknown test',
                'assertion': str(result.get('error') or 'test runner reported a failure'),
            })
        return details


    @staticmethod
    def unavailable(result):
        # True when the test runner itself could not run, so no test was executed.
        result = result or {}
        data = result.get('data') or {}
        if result.get('ok') is True or data.get('tests_run'):
            return False
        error = str(result.get('error') or '')
        return any(marker in error for marker in (
            'Docker is required',
            'AI_FRIEND_TEST_IMAGE',
            'functional test runner failed',
        ))
