ORGAN = {
    "name": "scaffold",
    "kind": "tool",
    "scope": "outside_guards",
    "capabilities": ["list_scaffolds", "read_scaffold", "apply_scaffold"],
    "security": {
        "requires": {
            "list_scaffolds": [
                "workspace.read",
            ],
            "read_scaffold": [
                "workspace.read",
            ],
            "apply_scaffold": [
                "workspace.read",
                "workspace.write",
            ],
        },
    },
    "keywords": [],
    "entry_module": "scaffold.scaffold",
    "entry_attr": "TOOLS",
}
