"""Config."""
from __future__ import annotations

import json
from pathlib import Path


DEFAULTS = {
    "model_provider": "ollama",
    "model_api_url": "http://localhost:11434",
    "model_name": "",
    "model_timeout": 120,
    "tool_budget": 40,
}


def load_config(workspace: Path) -> dict:
    path = Path(workspace) / ".central_mind" / "config.json"
    cfg = dict(DEFAULTS)
    if path.exists():
        try:
            user = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(user, dict):
                cfg.update(user)
        except Exception:
            pass
    return cfg


def save_default_config(workspace: Path) -> Path:
    path = Path(workspace) / ".central_mind" / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(DEFAULTS, indent=2), encoding="utf-8")
    return path