"""Ollama HTTP adapter. No subprocesses, model downloads, or authority changes."""
from __future__ import annotations

import os
import requests

try:
    from ..interface import ModelProvider
except ImportError:
    from interface import ModelProvider


class OllamaProvider(ModelProvider):
    name = "ollama"

    def __init__(self, api_url=None, model_name="", timeout=180):
        self.api_url = (api_url or os.environ.get("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
        if not self.api_url.startswith(("http://", "https://")):
            self.api_url = "http://" + self.api_url
        self.model_name = model_name
        self.timeout = timeout

    def models(self):
        response = requests.get(self.api_url + "/api/tags", timeout=min(self.timeout, 5))
        response.raise_for_status()
        return [item["name"] for item in response.json().get("models", []) if isinstance(item.get("name"), str)]

    def is_available(self):
        try:
            return self.model_name in self.models()
        except (requests.RequestException, ValueError, KeyError):
            return False

    def chat(self, messages, model_name=None, max_tokens=1024):
        model = model_name or self.model_name
        if not model:
            raise ValueError("Ollama execution model is required")
        response = requests.post(
            self.api_url + "/api/chat",
            json={"model": model, "messages": messages, "stream": False,
                  "options": {"num_predict": max_tokens}},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("error"):
            raise RuntimeError(str(data["error"]))
        content = (data.get("message") or {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Ollama returned no answer")
        return content

    def generate(self, prompt, system=None, max_tokens=1024):
        messages = ([{"role": "system", "content": system}] if system else [])
        return self.chat([*messages, {"role": "user", "content": prompt}], max_tokens=max_tokens)
