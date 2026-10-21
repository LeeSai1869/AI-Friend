"""Coding diagnosis through the shared capability resource."""
from .cognition import request_model


class Debugger:
    def diagnose(self, *, caller, task, evidence):
        return request_model(caller, capability='debug', messages=[{
            'role': 'user', 'content': f'Task: {task}\nObserved evidence:\n{evidence}\n'
            'Identify supported causes and a testable repair. Distinguish hypotheses from observed facts.',
        }])
