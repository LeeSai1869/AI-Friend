ORGAN = {
    "name": "folders",
    "kind": "tool",
    "scope": "outside_guards",
    "capabilities": ["create_folder"],
    "security": {
        "requires": {
            "create_folder": [
                "workspace.write",
            ],
        },
    },
    "keywords": [],
    "entry_module": "folders.folders",
    "entry_attr": "TOOLS",
}
