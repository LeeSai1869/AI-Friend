ORGAN = {
    "acceptance_check_kinds": ["python_call", "python_signature", "python_cli"],
    "acceptance_check_contracts": {
        "python_call": {"description": "Check a function against an explicit input/output example.",
            "payload": {"module": "Python module name", "function": "function name", "args": "JSON argument list", "kwargs": "JSON keyword mapping", "expected": "expected JSON result"}},
        "python_signature": {"description": "Check the exact declared parameters and annotations.",
            "payload": {"module": "Python module name", "function": "function name", "signature": "signature, e.g. (entries: list[str]) -> int"}},
        "python_cli": {"description": "Check an explicitly requested command-line interface.",
            "payload": {"script": "relative .py path", "args": "argument strings", "expected_exit": "integer exit code", "stdout_equals": "optional exact expected output"}},
    },
    "name": "coder",
    "domain_key": "coding",
    "kind": "domain",
    "scope": "outside_guards",
    "memory_domain": "Cod",
    "intake_processing": {"mode": "automatic", "capability": "examine_intake"},
    "display_name": "Coder",
    "icon": "💻",
    "window": "code",
    "capabilities": [
        "inspect_code", "plan_code", "write_code",
        "test_code", "debug_code", "verify_code",
        "application",
    ],

    # Semantic meaning is declared by the component itself so Central Mind
    # does not need Python keyword rules for coding intents.
    "capability_descriptions": {
        "inspect_code": (
            "Inspect and understand existing source code, project structure, "
            "implementation details, and relevant files without changing them."
        ),
        "plan_code": (
            "Design or explain a coding implementation plan before making "
            "changes; choose this when planning is the requested outcome."
        ),
        "write_code": (
            "Produce, implement, modify, refactor, or edit source code when "
            "the requested outcome is actual code rather than only a plan."
        ),
        "test_code": (
            "Test code or an implementation and report concrete test results."
        ),
        "debug_code": (
            "Diagnose a bug, failure, traceback, incorrect behavior, or broken "
            "implementation and determine or implement a correction."
        ),
        "verify_code": (
            "Verify that code or a coding change satisfies its stated "
            "requirements using available evidence and checks."
        ),
    },

    # Registry-facing model task identities.  These are declarative metadata,
    # not Central Mind routing rules.
    "model_routing_capabilities": {
        "inspect_code": "plan",
        "plan_code": "plan",
        "write_code": "write",
        "test_code": "test",
        "debug_code": "debug",
        "verify_code": "test",
    },

    # Read-only facts this domain can authoritatively provide to Central Mind
    # during reasoning. These are evidence capabilities, not execution routes.
    "evidence_capabilities": {
        "project_context": {
            "description": (
                "Report whether a Coding Project is currently open and, when "
                "open, provide its Coding-owned identity and bounded structural "
                "context without reading source contents or changing files."
            ),
            "read_only": True,
            "ambient": True,
        },
    },
    "keywords": [
        "code", "python", "bug", "debug", "function", "class",
        "script", "test", "file", "module", "refactor", "error",
        "traceback", "compile", "implement", "fix",
    ],
    "entry_module": "coding.coding_engine",
    "entry_attr": "ORGAN",
}