ORGAN = {
    "name": "general",
    "kind": "domain",
    "scope": "outside_guards",
    "memory_domain": "Gen",
    "display_name": "Chat",
    "icon": "💬",
    "window": "chat",
    "capabilities": ["chat"],
    "capability_descriptions": {
        "chat": (
            "Hold an ordinary conversation, answer general questions, explain "
            "information, and discuss AI Friend itself when no specialized "
            "action capability is the requested outcome."
        ),
    },
    "keywords": [],
    "entry_module": "general.general_engine",
    "entry_attr": "ORGAN",
}