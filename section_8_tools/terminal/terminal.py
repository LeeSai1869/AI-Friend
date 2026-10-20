"""Terminal execution tools.

Security contract:
- ``run_command`` is the legacy general process runner. Production Guard
  deliberately grants ``process.execute`` to nobody.
- ``run_python_compile`` is a constrained Coding V1 execution profile.
  Callers supply only workspace-relative Python paths. The executable and
  arguments are constructed here by trusted tool code.
"""
from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from _base.tool import Tool
from guard.contract import ToolEffect


def _result(proc: subprocess.CompletedProcess, command: List[str]) -> Dict[str, Any]:
    stdout = proc.stdout[-8000:] if len(proc.stdout) > 8000 else proc.stdout
    stderr = proc.stderr[-4000:] if len(proc.stderr) > 4000 else proc.stderr
    return {
        "ok": proc.returncode == 0,
        "data": {
            "command": command,
            "returncode": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
        },
        "error": None if proc.returncode == 0 else f"exit code {proc.returncode}",
    }


class RunCommand(Tool):
    """General process runner.

    This operation intentionally remains production-denied.  It exists for
    future explicitly-authorized execution contracts and compatibility, not
    as Coding V1's execution path.
    """

    name = "run_command"
    description = (
        "Run a program without a shell. Production policy intentionally "
        "does not grant this general execution operation."
    )
    parameters = {
        "command": "argument list; strings are split without shell operators",
        "cwd": "optional subfolder relative to workspace root",
        "timeout": "optional timeout in seconds (default 60)",
    }

    def effects(self, args: Dict[str, Any]) -> tuple[ToolEffect, ...]:
        raw = args.get("command")
        if isinstance(raw, str):
            try:
                command = shlex.split(raw)
            except ValueError as exc:
                raise ValueError(f"invalid command: {exc}") from exc
        elif isinstance(raw, list) and all(isinstance(p, str) for p in raw):
            command = raw
        else:
            raise ValueError("command must be a non-empty string or list of strings")

        if not command or not command[0]:
            raise ValueError("command is required")

        return (
            ToolEffect(
                action="execute",
                target=f"process:{command[0]}",
                scope="service",
            ),
        )

    def call(self, args: Dict[str, Any]) -> Dict[str, Any]:
        raw_command = args.get("command")
        if isinstance(raw_command, str):
            try:
                command = shlex.split(raw_command)
            except ValueError as exc:
                return {"ok": False, "data": None, "error": f"invalid command: {exc}"}
        elif isinstance(raw_command, list) and all(
            isinstance(part, str) for part in raw_command
        ):
            command = raw_command
        else:
            return {
                "ok": False,
                "data": None,
                "error": "command must be a non-empty string or list of strings",
            }

        if not command or not command[0]:
            return {"ok": False, "data": None, "error": "command is required"}

        cwd = args.get("cwd") or ""
        try:
            timeout = int(args.get("timeout") or 60)
        except (TypeError, ValueError):
            return {"ok": False, "data": None, "error": "timeout must be an integer"}

        if timeout < 1 or timeout > 120:
            return {
                "ok": False,
                "data": None,
                "error": "timeout must be between 1 and 120 seconds",
            }

        try:
            target = self._resolve(cwd) if cwd else self.workspace_root
        except ValueError as exc:
            return {"ok": False, "data": None, "error": str(exc)}

        if not target.exists() or not target.is_dir():
            return {"ok": False, "data": None, "error": f"cwd not found: {cwd}"}

        try:
            proc = subprocess.run(
                command,
                shell=False,
                cwd=str(target),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "data": None, "error": f"timeout after {timeout}s"}
        except Exception as exc:
            return {"ok": False, "data": None, "error": str(exc)}

        return _result(proc, command)


class RunPythonCompile(Tool):
    """Compile-check workspace Python files under a fixed execution profile."""

    name = "run_python_compile"
    description = (
        "Run Python py_compile only for validated workspace-relative .py files."
    )
    parameters = {
        "paths": "non-empty list of workspace-relative .py file paths",
        "timeout": "optional timeout in seconds (default 60, maximum 120)",
    }

    def _validated_paths(self, args: Dict[str, Any]) -> List[str]:
        paths = args.get("paths")

        if (
            not isinstance(paths, list)
            or not paths
            or not all(isinstance(path, str) and path.strip() for path in paths)
        ):
            raise ValueError("paths must be a non-empty list of strings")

        if len(paths) > 50:
            raise ValueError("at most 50 Python files may be checked at once")

        normalized: List[str] = []

        for raw in paths:
            value = raw.strip()

            if not value.lower().endswith(".py"):
                raise ValueError(f"only .py files may be compiled: {value}")

            resolved = self._resolve(value)

            if not resolved.exists():
                raise ValueError(f"Python file not found: {value}")

            if not resolved.is_file():
                raise ValueError(f"Python target is not a file: {value}")

            normalized.append(
                resolved.relative_to(self.workspace_root).as_posix()
            )

        return normalized

    def effects(self, args: Dict[str, Any]) -> tuple[ToolEffect, ...]:
        # Validation occurs during effect preflight, before Guard authorization
        # and before executable tool control.
        self._validated_paths(args)

        return (
            ToolEffect(
                action="execute",
                target="code-test:python-py_compile",
                scope="service",
            ),
        )

    def call(self, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            paths = self._validated_paths(args)
        except ValueError as exc:
            return {"ok": False, "data": None, "error": str(exc)}

        try:
            timeout = int(args.get("timeout") or 60)
        except (TypeError, ValueError):
            return {"ok": False, "data": None, "error": "timeout must be an integer"}

        if timeout < 1 or timeout > 120:
            return {
                "ok": False,
                "data": None,
                "error": "timeout must be between 1 and 120 seconds",
            }

        command = ["python3", "-m", "py_compile", *paths]

        try:
            proc = subprocess.run(
                command,
                shell=False,
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "data": None, "error": f"timeout after {timeout}s"}
        except Exception as exc:
            return {"ok": False, "data": None, "error": str(exc)}

        return _result(proc, command)


TOOLS = [RunCommand, RunPythonCompile]
