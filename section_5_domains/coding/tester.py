"""Coding's test coordinator. Execution belongs exclusively to guarded tools."""
from __future__ import annotations


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
