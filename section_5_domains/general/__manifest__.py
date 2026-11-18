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
    "evidence_capabilities": {
        "app_self_description": {
            "description": (
                "Return a curated, read-only description of AI Friend itself: what Raw, Tested and Derived Memory are, "
                "the user roles, the Central Mind loops, which domains exist and what the app can and cannot do today. "
                "Consult this for questions about what the app is, how it works or what it can access, and before asking "
                "the user about the app. It describes the app; it does not report live state such as which project is open."
            ),
            "read_only": True,
            "ambient": True,
        },
    },
    "keywords": [],
    "entry_module": "general.general_engine",
    "entry_attr": "ORGAN",
}