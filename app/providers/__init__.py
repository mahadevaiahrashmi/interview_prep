"""Provider registry and lookup."""
from __future__ import annotations

from .base import LLMProvider, ProviderError
from .claude_cli import ClaudeCLIProvider
from .gemini_cli import GeminiCLIProvider
from .mock import MockProvider
from .ollama import OllamaProvider
from .openrouter import OpenRouterProvider

PROVIDERS: dict[str, type[LLMProvider]] = {
    "claude": ClaudeCLIProvider,
    "gemini": GeminiCLIProvider,
    "ollama": OllamaProvider,
    "openrouter": OpenRouterProvider,
    "mock": MockProvider,
}

_NEEDS_MODEL = {"claude", "gemini", "ollama", "openrouter"}


def get_provider(name: str | None, model: str | None = None) -> LLMProvider:
    key = (name or "mock").lower()
    cls = PROVIDERS.get(key)
    if cls is None:
        raise ProviderError(
            f"Unknown provider '{name}'. Choose from {sorted(PROVIDERS)}."
        )
    if key in _NEEDS_MODEL and model:
        return cls(model=model)
    return cls()


def list_providers(include_models: bool = False) -> list[dict]:
    """Provider metadata for the UI: name, label, availability, (optional) models.

    `include_models` shells out for Ollama's installed list, so it's only set on
    the JSON endpoint the browser fetches, not the initial template render.
    """
    out = []
    for key, cls in PROVIDERS.items():
        inst = cls()
        entry = {
            "name": key,
            "label": inst.label,
            "available": inst.is_available(),
        }
        if include_models:
            entry["models"] = inst.suggested_models()
        out.append(entry)
    return out


__all__ = [
    "LLMProvider",
    "ProviderError",
    "ClaudeCLIProvider",
    "GeminiCLIProvider",
    "OllamaProvider",
    "OpenRouterProvider",
    "MockProvider",
    "PROVIDERS",
    "get_provider",
    "list_providers",
]
