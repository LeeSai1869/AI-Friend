"""Behavior checks run only inside the existing guarded test container."""
import hashlib
import json
import re


def acceptance_module(checks):
    if not isinstance(checks, list) or len(checks) > 32:
        raise ValueError('acceptance checks must contain at most 32 checks')
    seen = set()
    for check in checks:
        if not isinstance(check, dict) or check.get('kind') not in {'python_call', 'python_signature', 'python_cli'}:
            raise ValueError('unsupported Coding acceptance check')
        identity = check.get('id')
        if not isinstance(identity, str) or not identity or identity in seen:
            raise ValueError('acceptance checks require unique nonempty identities')
        seen.add(identity)
        payload = check.get('payload') or {}
        if not isinstance(payload, dict):
            raise ValueError('acceptance payload must be an object')
        if check['kind'] == 'python_cli':
            from pathlib import PurePosixPath
            script = PurePosixPath(str(payload.get('script', '')))
            if script.is_absolute() or '..' in script.parts or script.suffix != '.py':
                raise ValueError('CLI acceptance checks require a relative Python script')
            if not isinstance(payload.get('args', []), list) or any(not isinstance(arg, str) for arg in payload.get('args', [])):
                raise ValueError('CLI arguments must be strings')
            if type(payload.get('expected_exit')) is not int:
                raise ValueError('CLI check must declare expected_exit')
            continue
        if not re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*', str(payload.get('module', ''))):
            raise ValueError('acceptance module must name a Python module')
        if not re.fullmatch(r'[A-Za-z_]\w*', str(payload.get('function', ''))):
            raise ValueError('acceptance function must name a Python function')
        if check['kind'] == 'python_call':
            if not isinstance(payload.get('args', []), list) or not isinstance(payload.get('kwargs', {}), dict) or 'expected' not in payload:
                raise ValueError('python_call needs args, kwargs and an expected result')
        else:
            import ast
            signature = ast.parse('def target' + str(payload.get('signature', '')) + ':\n    pass\n')
            if len(signature.body) != 1 or not isinstance(signature.body[0], ast.FunctionDef):
                raise ValueError('expected one function signature')
    encoded = json.dumps(checks, ensure_ascii=True, allow_nan=False)
    if len(encoded) > 64000:
        raise ValueError('acceptance checks exceed the context budget')
    name = 'test_ai_friend_acceptance_' + hashlib.sha256(encoded.encode()).hexdigest()[:16] + '.py'
    code = ('import unittest, json, importlib, ast, subprocess, sys\nfrom pathlib import Path\n'
            + 'CHECKS = json.loads(' + repr(encoded) + ')\n'
            + 'class AcceptanceTests(unittest.TestCase):\n')
    for i, check in enumerate(checks):
        code += f'    def test_case_{i}(self):\n        check = CHECKS[{i}]\n        payload = check["payload"]\n'
        if check['kind'] == 'python_cli':
            code += ('        run = subprocess.run([sys.executable, payload["script"], *payload.get("args", [])], capture_output=True, text=True, timeout=5)\n'
                     '        self.assertEqual(run.returncode, payload["expected_exit"], check["id"] + ": " + run.stderr)\n'
                     '        if "stdout_equals" in payload: self.assertEqual(run.stdout.strip(), payload["stdout_equals"].strip(), check["id"])\n')
        elif check['kind'] == 'python_call':
            code += ('        target = getattr(importlib.import_module(payload["module"]), payload["function"])\n'
                     '        self.assertEqual(target(*payload.get("args", []), **payload.get("kwargs", {})), payload["expected"], check["id"])\n')
        else:
            code += ('        source = Path(*payload["module"].split(".")).with_suffix(".py").read_text()\n'
                     '        actual = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == payload["function"])\n'
                     '        expected = ast.parse("def target" + payload["signature"] + ":\\n    pass\\n").body[0]\n'
                     '        self.assertEqual(ast.dump(actual.args), ast.dump(expected.args), check["id"])\n'
                     '        self.assertEqual(ast.dump(actual.returns) if actual.returns else None, ast.dump(expected.returns) if expected.returns else None, check["id"])\n')
    return name, code
