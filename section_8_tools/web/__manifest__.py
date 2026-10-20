ORGAN = {
    "name": "web",
    "kind": "tool",
    "scope": "outside_guards",
    "capabilities": ["web_search", "web_fetch"],
    "security": {
        "requires": {
            "web_search": [
                "network.access",
            ],
            "web_fetch": [
                "network.access",
            ],
        },
    },
    "keywords": [],
    "entry_module": "web.web",
    "entry_attr": "TOOLS",
}
