"""Functional Python unittest profile: disposable container, no host mounts/network."""
from __future__ import annotations

import json
import io
import tarfile
import time
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
import uuid

from _base.tool import Tool
from guard.contract import ToolEffect


_RUNNER = r'''
import ast, contextlib, importlib, io, json, os, pathlib, sys, unittest
packet = json.load(sys.stdin)
root = pathlib.Path('/work')
for name, content in packet['files'].items():
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')
sys.path.insert(0, str(root))
use_pytest = any(
    any((isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('test_'))
        or (isinstance(node, ast.Import) and any(alias.name == 'pytest' for alias in node.names))
        or (isinstance(node, ast.ImportFrom) and node.module == 'pytest')
        for node in ast.parse(packet['files'][name]).body)
    for name in packet['tests']
)
if use_pytest:
    try:
        os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
        import pytest
    except ImportError:
        print('\nAI_FRIEND_TEST_RESULT=' + json.dumps(dict(
            tests_run=0, passed=0, failures=0, errors=1, skipped=0,
            expected_failures=0, unexpected_successes=0,
            output='Install pytest in the configured test image.')))
        sys.exit(2)
    class Evidence:
        passed = failures = errors = skipped = expected_failures = unexpected_successes = 0
        def pytest_runtest_logreport(self, report):
            if report.when == 'call':
                if report.passed:
                    if hasattr(report, 'wasxfail'):
                        self.unexpected_successes += 1
                    else:
                        self.passed += 1
                elif report.failed:
                    self.failures += 1
                elif hasattr(report, 'wasxfail'):
                    self.expected_failures += 1
                else:
                    self.skipped += 1
            elif report.failed:
                self.errors += 1
            elif report.skipped:
                self.skipped += 1
        def pytest_collectreport(self, report):
            if report.failed:
                self.errors += 1
    evidence = Evidence()
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
        code = pytest.main(['-q', '-p', 'no:cacheprovider', *packet['tests']], plugins=[evidence])
    report = dict(tests_run=evidence.passed + evidence.failures + evidence.skipped + evidence.expected_failures + evidence.unexpected_successes,
                  passed=evidence.passed, failures=evidence.failures, errors=evidence.errors,
                  skipped=evidence.skipped, expected_failures=evidence.expected_failures,
                  unexpected_successes=evidence.unexpected_successes, output=stream.getvalue()[-12000:],
                  framework='pytest')
    print('\nAI_FRIEND_TEST_RESULT=' + json.dumps(report), flush=True)
    sys.exit(0 if int(code) == 0 and evidence.passed > 0 else 1)
suite = unittest.TestSuite()
for name in packet['tests']:
    module = importlib.import_module('.'.join(pathlib.PurePosixPath(name).with_suffix('').parts))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
stream = io.StringIO()
result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
passed = max(0, result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)
             - len(result.expectedFailures) - len(result.unexpectedSuccesses))
report = dict(tests_run=result.testsRun, passed=passed, failures=len(result.failures),
              errors=len(result.errors), skipped=len(result.skipped),
              expected_failures=len(result.expectedFailures), unexpected_successes=len(result.unexpectedSuccesses),
              output=stream.getvalue()[-12000:], framework='unittest')
print('\nAI_FRIEND_TEST_RESULT=' + json.dumps(report), flush=True)
sys.exit(0 if result.wasSuccessful() and passed > 0 else 1)
'''


def runtime_image():
    configured=os.environ.get('AI_FRIEND_TEST_IMAGE')
    if configured is not None:
        return configured.strip()
    path=Path.home()/'Library/Application Support/AI Friend V1/runtime/test-image-id'
    return path.read_text().strip() if path.is_file() else ''


def docker_executable():
    executable=shutil.which('docker')
    if executable:return executable
    bundled=Path('/Applications/Docker.app/Contents/Resources/bin/docker')
    return str(bundled) if bundled.is_file() and os.access(bundled,os.X_OK) else None


class RunPythonTests(Tool):
    name = 'run_python_tests'
    description = 'Run selected Python unittest or pytest modules in a resource-limited isolated source snapshot.'
    parameters = {'paths': 'selected Python test modules', 'sources': 'explicit UTF-8 source and fixture snapshot paths',
                  'overrides': 'optional candidate content by relative path', 'timeout': 'seconds, 1..60'}
    MAX_FILES = 200
    MAX_BYTES = 4 * 1024 * 1024

    def _validate(self, args):
        sources, tests = args.get('sources'), args.get('paths')
        overrides = args.get('overrides') or {}
        if not isinstance(sources, list) or not sources or len(sources) > self.MAX_FILES:
            raise ValueError('sources must contain 1..200 source or fixture paths')
        if not isinstance(tests, list) or not tests or len(tests) > 50:
            raise ValueError('paths must contain 1..50 unittest modules')
        if not isinstance(overrides, dict) or any(not isinstance(v, str) for v in overrides.values()):
            raise ValueError('overrides must map paths to text')
        paths = list(dict.fromkeys(sources))
        for value in paths + list(overrides) + tests:
            if not isinstance(value, str) or not value or '\\' in value:
                raise ValueError('Python paths must be relative POSIX paths')
            pure = PurePosixPath(value)
            if pure.is_absolute() or '..' in pure.parts or pure.as_posix() != value:
                raise ValueError('snapshot paths must be normalized relative files')
            if value in tests and pure.suffix != '.py':
                raise ValueError('test modules must be .py files')
            if value in tests and any(not part.isidentifier() for part in pure.with_suffix('').parts):
                raise ValueError('test snapshot paths must be importable Python module paths')
            target = self._resolve(value)
            if value not in overrides and (not target.is_file() or target.is_symlink()):
                raise ValueError('source is missing or not a regular file: ' + value)
        if not set(tests).issubset(paths) or not set(overrides).issubset(paths):
            raise ValueError('tests and overrides must belong to the explicit source snapshot')
        timeout = args.get('timeout', 30)
        if type(timeout) is not int or not 1 <= timeout <= 60:
            raise ValueError('timeout must be an integer between 1 and 60')
        return paths, tests, overrides, timeout

    def effects(self, args):
        paths, _, overrides, _ = self._validate(args)
        return tuple(ToolEffect(action='read', target=str(self._resolve(path)), scope='exact')
                     for path in paths if path not in overrides) + (
            ToolEffect(action='execute', target='code-test:python-unittest-container', scope='service'),
        )

    def call(self, args):
        try:
            paths, tests, overrides, timeout = self._validate(args)
            image = runtime_image()
            if not re.fullmatch(r'(?:[A-Za-z0-9_./:-]+@)?sha256:[a-f0-9]{64}', image):
                raise ValueError('configure AI_FRIEND_TEST_IMAGE with a locally installed digest-pinned Python image')
            docker = docker_executable()
            if not docker:
                raise ValueError('Docker is required for isolated functional testing')
            files = {}
            size = 0
            for path in paths:
                if path in overrides:
                    content = overrides[path]
                else:
                    target = self._resolve(path)
                    if target.stat().st_size > self.MAX_BYTES:
                        raise ValueError('source snapshot exceeds the 4 MiB budget')
                    content = target.read_text(encoding='utf-8')
                size += len(content.encode('utf-8'))
                if size > self.MAX_BYTES:
                    raise ValueError('source snapshot exceeds the 4 MiB budget')
                files[path] = content
            packet = json.dumps({'files': files, 'tests': tests})
        except (ValueError, OSError, TypeError) as exc:
            return {'ok': False, 'data': None, 'error': str(exc)}
        name = 'ai-friend-test-' + uuid.uuid4().hex
        bootstrap = "import os,sys; os.chdir('/work'); sys.stdin=open('/work/.input.json', encoding='utf-8');\n" + _RUNNER
        command = [docker, 'create', '--name', name, '--pull=never',
                   '--network=none', '--cap-drop=ALL',
                   '--security-opt=no-new-privileges', '--pids-limit=64',
                   '--memory=512m', '--cpus=2', '--user=65534:65534',
                   image, 'python', '-I', '-c', bootstrap]
        deadline = time.monotonic() + timeout
        def remaining():
            value = deadline - time.monotonic()
            if value <= 0:
                raise subprocess.TimeoutExpired(command, timeout)
            return value
        def control(cmd, **kwargs):
            proc = subprocess.run(cmd, capture_output=True, timeout=remaining(), **kwargs)
            if proc.returncode != 0:
                raise RuntimeError("container " + cmd[1] + " failed")
            return proc
        try:
            control(command)
            # Staging uses Docker's archive API, not stdin attachment or a host
            # mount. The container cannot run user tests until staging completes.
            archive = io.BytesIO()
            with tarfile.open(fileobj=archive, mode='w') as tar:
                directory = tarfile.TarInfo('work')
                directory.type = tarfile.DIRTYPE
                directory.mode = 0o777
                tar.addfile(directory)
                encoded = packet.encode('utf-8')
                entry = tarfile.TarInfo('work/.input.json')
                entry.size, entry.mode = len(encoded), 0o444
                tar.addfile(entry, io.BytesIO(encoded))
            control([docker, 'cp', '-', name + ':/'], input=archive.getvalue())
            control([docker, 'start', name])
            waited = control([docker, 'wait', name])
            exit_code = int(waited.stdout.decode('ascii').strip())
            with tempfile.TemporaryFile(mode='w+b') as out, tempfile.TemporaryFile(mode='w+b') as err:
                result = subprocess.run([docker, 'logs', name], stdout=out, stderr=err, timeout=remaining())
                if result.returncode != 0:
                    raise RuntimeError('container logs unavailable')
                out.seek(0, 2)
                out.seek(max(0, out.tell() - 65536))
                stdout = out.read().decode('utf-8', errors='replace')
                err.seek(0, 2)
                err.seek(max(0, err.tell() - 4096))
                stderr = err.read().decode('utf-8', errors='replace')
            marker = '\nAI_FRIEND_TEST_RESULT='
            if marker not in stdout:
                return {'ok': False, 'data': {'returncode': exit_code,
                        'stderr': stderr}, 'error': 'test runner did not produce a result'}
            data = json.loads(stdout.rsplit(marker, 1)[1].strip())
            data['returncode'] = exit_code
            ok = (exit_code == 0 and type(data.get('tests_run')) is int and data['tests_run'] > 0
                  and type(data.get('passed')) is int and data['passed'] > 0
                  and data.get('failures') == 0 and data.get('errors') == 0
                  and data.get('unexpected_successes') == 0)
            data['profile'] = 'isolated_python_tests'
            return {'ok': ok, 'data': data, 'error': None if ok else 'functional tests failed or no assertions ran'}
        except subprocess.TimeoutExpired:
            return {'ok': False, 'data': None, 'error': 'functional tests timed out'}
        except (OSError, ValueError, TypeError, RuntimeError) as exc:
            return {'ok': False, 'data': None, 'error': 'functional test runner failed: ' + type(exc).__name__}
        finally:
            # Only our uniquely named container is eligible for cleanup.
            try:
                subprocess.run([docker, 'rm', '--force', name], capture_output=True, timeout=10)
            except (OSError, subprocess.TimeoutExpired):
                pass  # Never replace the underlying test result with a cleanup error.
