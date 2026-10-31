ORGAN = {
    "name": "web",
    "kind": "tool",
    "scope": "outside_guards",
    "capabilities": ["web_search", "web_fetch", "browser_interact", "browser_media"],
    "security": {
        "requires": {
            "browser_media": ["network.access"],
            "browser_interact": ["network.access"],
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
