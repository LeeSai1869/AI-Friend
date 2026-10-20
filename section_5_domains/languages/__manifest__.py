"""Languages domain manifest.

Rosters cite section_7_models/models_registry.yaml.
Do not invent LLMs here. Every name in `models` must exist
as a top-level key in the registry under `llms:`.

The mind's router reads the registry and routes by these keys.
"""
ORGAN = {
    "name": "languages",
    "kind": "domain",
    "domain_key": "languages",
    "scope": "outside_guards",
    "memory_domain": "Lng",
    "display_name": "Languages",
    "icon": "🌐",
    "window": "chat",
    "capabilities": ["learn", "read", "translate", "write", "detect"],

    # Rosters cite the registry. Order is a default;
    # memory evidence reorders it at runtime.
    "models": {
        "translate": ["aya-expanse_8b", "gemma4_26b", "llama3.1_8b"],
        "read":      ["gemma4_26b", "aya-expanse_8b", "llama3.1_8b"],
        "write":     ["gemma4_26b", "llama3.1_8b", "aya-expanse_8b"],
        "detect":    ["llama3.1_8b", "gemma4_26b"],
    },

    "keywords": [
        "language", "translate", "translation", "urdu", "mandarin",
        "chinese", "hindi", "spanish", "arabic", "french", "german",
        "english", "script", "vocabulary", "grammar",
    ],
    "entry_module": "languages.languages_engine",
    "entry_attr": "ORGAN",
}
