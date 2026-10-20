ORGAN = {
    "name": "terminal",
    "kind": "tool",
    "scope": "outside_guards",
    "capabilities": [
        "run_command",
        "run_python_compile",
    ],
    "security": {
        "requires": {
            # Deliberately remains unavailable in production.
            "run_command": [
                "process.execute",
            ],

            # Narrow Coding V1 execution authority.
            "run_python_compile": [
                "code.test.execute",
            ],
        },
    },
    "keywords": [],
    "entry_module": "terminal.terminal",
    "entry_attr": "TOOLS",
}
