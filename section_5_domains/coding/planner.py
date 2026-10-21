"""Read-only planning through the shared capability caller."""
from __future__ import annotations

from .cognition import request_model


class Planner:
    def plan(self, *, task, caller, evidence, recalled=''):
        return request_model(caller, capability='plan', messages=[{
            'role': 'user',
            'content': (f'Task: {task}\nProject evidence:\n{evidence}\nRecalled evidence:\n{recalled}\n'
                        'Produce an implementation plan only. State file targets, dependencies, '
                        'behavioral tests, risks, and unresolved information. Do not claim any changes were made.'),
        }])
