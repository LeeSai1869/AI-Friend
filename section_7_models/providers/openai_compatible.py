"""OpenAI-compatible chat adapter, independent of any model identity."""
from __future__ import annotations

import requests
try:
    from ..interface import ModelProvider
except ImportError:
    from interface import ModelProvider


class OpenAICompatibleProvider(ModelProvider):
    name = "openai_compatible"

    def __init__(self, api_url, api_key="", model_name="", timeout=180):
        if not api_url:
            raise ValueError("OpenAI-compatible api_url is required")
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout

    def chat(self, messages, model_name=None, max_tokens=1024):
        headers = {"Authorization": "Bearer " + self.api_key} if self.api_key else {}
        response = requests.post(
            self.api_url + "/chat/completions",
            headers=headers,
            json={"model": model_name or self.model_name, "messages": messages,
                  "max_tokens": max_tokens},
            timeout=self.timeout,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("provider returned no answer")
        return content

    def generate(self, prompt, system=None, max_tokens=1024):
        messages = ([{"role": "system", "content": system}] if system else [])
        return self.chat([*messages, {"role": "user", "content": prompt}], max_tokens=max_tokens)
