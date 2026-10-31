"""The subordinate model-resource caller.

Two ways to call a model:

  1. `call(model_name, messages)` — call a specific model organ by
     name. Used when the caller already knows which model it wants.

  2. `route(domain, capability, messages)` — ask the registry for
     the priority list of LLMs for this domain + capability, then
     try them in order. The first acceptable result wins. The
     caller records which LLM succeeded, so the domain can attach
     a source tag to memory.

The mind owns one Caller. Any organ that needs a model calls it.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Callable
import json


class Caller:

    def __init__(self, inventory, loader, router=None, ollama_url: str = "http://localhost:11434", memory=None, on_status=None):
        self.inventory = inventory
        self._load = loader  # a callable that returns the organ instance
        self.router = router
        self.memory = memory
        self.on_status = on_status
        self.last_execution = {}
        self.ollama_url = ollama_url
        # The source of the last successful routed call. Domains
        # read this to attach a source tag when writing memory.
        self.last_source: Optional[Dict[str, Any]] = None

    # -----------------------------------------------------------------
    # Direct model call — call a model organ by name.
    # -----------------------------------------------------------------
    def call(
        self,
        model_name: str,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        max_tokens: int = 2048,
    ) -> str:
        info = self.inventory.get(model_name)
        if info is None or info.kind != "model":
            raise ValueError(f"unknown model: {model_name}")

        organ = self._load(info)
        if organ is None:
            raise RuntimeError(f"could not load model: {model_name}")

        final_messages: List[Dict[str, str]] = []
        if system:
            final_messages.append({"role": "system", "content": system})
        final_messages.extend(messages)

        try:
            result = organ.handle({
                "messages": final_messages,
                "max_tokens": max_tokens,
            })
        except Exception as e:
            raise RuntimeError(f"model {model_name} raised: {e}")

        if not isinstance(result, dict):
            return str(result)

        if result.get("status") == "ok":
            return result.get("output", "")
        return f"[model error] {result.get('error', 'unknown error')}"

    # -----------------------------------------------------------------
    # Routed call — read the registry, try LLMs in priority order.
    # -----------------------------------------------------------------
    def route(
        self,
        domain: str,
        capability: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 2048,
        max_attempts: Optional[int] = None,
        source_scores=None,
        structured_output: Optional[str] = None,
    ) -> str:
        """Route a request to the registry-declared priority list.

        Returns the first acceptable output. Records which LLM
        produced it in self.last_source.

        Raises RuntimeError if all LLMs in the roster fail.
        """
        self.last_source = None
        self.last_execution = {}
        if self.router is None:
            raise RuntimeError("no router attached to caller")
        if source_scores is None and self.memory is not None:
            try:
                source_scores = self.memory.source_scores(domain=domain, capability=capability)
            except Exception:
                source_scores = {}
        from functools import partial

        attempts: List[Dict[str, Any]] = []

        protocol = {"structured_output":structured_output} if structured_output is not None else {}
        for attempt in self.router.try_capability(
            domain=domain,
            capability=capability,
            call_fn=partial(self._invoke_resource, max_tokens=max_tokens, operation=f"{domain}/{capability}"),
            messages=messages,
            max_attempts=max_attempts,
            source_scores=source_scores,
            **protocol,
        ):
            attempts.append(attempt)
            if attempt.get("ok"):
                self.last_source = {
                    "type": "model",
                    "name": attempt["model"],
                    "capability": capability,
                    "organ": domain,
                    **self.last_execution,
                }
                return attempt["output"]

        # All failed. Raise with a diagnostic.
        raise RuntimeError(
            f"routing failed for {domain}.{capability}. "
            f"attempts={json.dumps(attempts)[:500]}"
        )

    # -----------------------------------------------------------------
    # Generic model-resource execution.
    # -----------------------------------------------------------------
    def _invoke_resource(
        self,
        llm_key: str,
        resource: Dict[str, Any],
        messages: List[Dict[str, str]],
        max_tokens=2048,
        operation=None,
    ) -> str:
        try:
            from interface import (
                build_resource_provider,
                execution_model_for,
            )
        except ImportError:
            from section_7_models.interface import (
                build_resource_provider,
                execution_model_for,
            )

        provider = build_resource_provider(
            resource,
            timeout=300,
        )
        execution_model = execution_model_for(resource)

        if not execution_model:
            raise RuntimeError(
                f"model resource {llm_key} has no execution identifier"
            )

        if callable(self.on_status):
            self.on_status(f"Using model resource {llm_key} ({provider.name})" + (f" · {operation}" if operation else "") + "…")
        output = provider.chat(messages, model_name=execution_model, max_tokens=max_tokens)
        self.last_execution = {"provider": provider.name, "execution_model": execution_model}
        return output
