ORGAN = {
    "name": "filesystem",
    "kind": "tool",
    "scope": "outside_guards",
    "capabilities": ["list_files", "read_file", "search_files", "write_file"],
    "security": {
        "requires": {
            "list_files": [
                "workspace.read",
            ],
            "read_file": [
                "workspace.read",
            ],
            "search_files": [
                "workspace.read",
            ],
            "write_file": [
                "workspace.write",
            ],
        },
    },
    "keywords": [],
    "entry_module": "filesystem.filesystem",
    "entry_attr": "TOOLS",
}
