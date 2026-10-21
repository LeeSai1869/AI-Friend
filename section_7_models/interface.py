"""Generic model-provider interface and provider factory.

Central Mind selects model resources.  A model resource declares how it is
executed.  Providers perform only the mechanical runtime call.

The default provider remains Ollama for legacy registry entries that contain
an ``ollama_tag`` but do not yet declare an explicit provider.
"""
from __future__ import annotations

from typing import Any, Dict


class ModelProvider:
    name: str = "base"

    def generate(self, prompt, system=None, max_tokens=1024):
        raise NotImplementedError

    def chat(self, messages, model_name=None, max_tokens=1024):
        raise NotImplementedError

    def is_available(self) -> bool:
        return True


def provider_name_for(resource: Dict[str, Any]) -> str:
    """Resolve the execution provider for a registry model resource."""
    explicit = (
        resource.get("provider")
        or resource.get("runtime")
        or resource.get("model_provider")
    )

    if explicit:
        return str(explicit).strip().lower()

    # Backward-compatible migration rule. Existing registry resources are
    # Ollama resources because their execution identity is an ollama_tag.
    if resource.get("ollama_tag"):
        return "ollama"

    return ""


def execution_model_for(resource: Dict[str, Any]) -> str:
    """Return the provider-specific model identifier."""
    provider = provider_name_for(resource)

    if provider == "ollama":
        return str(
            resource.get("ollama_tag")
            or resource.get("model_name")
            or ""
        ).strip()

    return str(
        resource.get("model_name")
        or resource.get("model_path")
        or resource.get("path")
        or resource.get("local_path")
        or resource.get("repo")
        or ""
    ).strip()


def build_resource_provider(
    resource: Dict[str, Any],
    *,
    timeout: int = 180,
) -> ModelProvider:
    """Construct the provider declared by a model resource."""
    provider = provider_name_for(resource)

    if provider == "ollama":
        try:
            from .providers.ollama import OllamaProvider
        except (ImportError, ValueError):
            from providers.ollama import OllamaProvider

        return OllamaProvider(
            api_url=resource.get("api_url"),
            model_name=execution_model_for(resource),
            timeout=resource.get("timeout", timeout),
            generation=resource.get("_generation"),
        )

    if provider in {"transformers", "huggingface", "hf"}:
        try:
            from .providers.transformers_local import TransformersProvider
        except (ImportError, ValueError):
            from providers.transformers_local import TransformersProvider

        return TransformersProvider(
            model_name=execution_model_for(resource),
            timeout=resource.get("timeout", timeout),
            local_files_only=resource.get("local_files_only", True),
            task=resource.get("task", "text2text-generation"),
        )

    if provider in {"mlx", "mlx_lm", "mlx-lm"}:
        try:
            from .providers.mlx_local import MLXProvider
        except (ImportError, ValueError):
            from providers.mlx_local import MLXProvider

        return MLXProvider(
            model_name=execution_model_for(resource),
            timeout=resource.get("timeout", timeout),
        )

    if provider == "whisperkit":
        try:
            from .providers.whisperkit import WhisperKitProvider
        except (ImportError, ValueError):
            from providers.whisperkit import WhisperKitProvider

        return WhisperKitProvider(
            model_name=resource.get("model_name") or "",
            model_path=resource.get("model_path") or resource.get("path") or "",
            timeout=resource.get("timeout", 600),
        )

    if provider in {"mflux", "flux"}:
        try:
            from .providers.mflux import MFluxProvider
        except (ImportError, ValueError):
            from providers.mflux import MFluxProvider

        return MFluxProvider(
            model_name=execution_model_for(resource),
            timeout=resource.get("timeout", 900),
        )

    if provider in {"openai", "openai_compat", "http"}:
        try:
            from .providers.openai_compatible import OpenAICompatibleProvider
        except (ImportError, ValueError):
            from providers.openai_compatible import OpenAICompatibleProvider

        return OpenAICompatibleProvider(
            api_url=resource.get("api_url") or "",
            api_key=resource.get("api_key") or "",
            model_name=execution_model_for(resource),
            timeout=resource.get("timeout", timeout),
            generation=resource.get("_generation"),
        )

    raise ValueError(
        f"unsupported or missing model provider: {provider or '(none)'}"
    )


def build_provider(config: dict) -> ModelProvider:
    """Compatibility factory for the older application config contract."""
    provider = (config.get("model_provider") or "ollama").lower()

    if provider == "ollama":
        try:
            from .providers.ollama import OllamaProvider
        except (ImportError, ValueError):
            from providers.ollama import OllamaProvider

        return OllamaProvider(
            api_url=config.get("model_api_url") or "http://localhost:11434",
            model_name=config.get("model_name") or "",
            timeout=config.get("model_timeout", 120),
        )

    if provider in {"openai", "openai_compat", "http"}:
        try:
            from .providers.openai_compatible import OpenAICompatibleProvider
        except (ImportError, ValueError):
            from providers.openai_compatible import OpenAICompatibleProvider

        return OpenAICompatibleProvider(
            api_url=config.get("model_api_url") or "",
            api_key=config.get("model_api_key") or "",
            model_name=config.get("model_name") or "",
            timeout=config.get("model_timeout", 60),
        )

    raise ValueError(f"unsupported model provider: {provider}")
