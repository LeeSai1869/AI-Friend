ORGAN = {
    "name": "intake",
    "kind": "tool",
    "scope": "outside_guards",
    "capabilities": ["intake_propose", "intake_commit"],
    "security": {
        "requires": {
            "intake_propose": [
                "workspace.read",
                "workspace.write",
                "knowledge.propose",
            ],
            "intake_commit": [
                "knowledge.propose",
            ],
        },
    },
    "keywords": [],
    "entry_module": "intake.intake",
    "entry_attr": "TOOLS",
}
