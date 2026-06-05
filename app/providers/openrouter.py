"""OpenRouter provider — hosted access to DeepSeek, Qwen, and many others.

Unlike the CLI engines, this one talks to OpenRouter's OpenAI-compatible HTTP
API, so it needs an API key. The key is read from the environment and is never
stored by the app. Get one at https://openrouter.ai/keys.

Config via environment:
  OPENROUTER_API_KEY  required; your OpenRouter key (e.g. "sk-or-...")
  OPENROUTER_MODEL    model id (default: "deepseek/deepseek-chat"); override per
                      run via the model box, e.g. "qwen/qwen-2.5-72b-instruct"
"""
from __future__ import annotations

import os

import httpx

from .base import LLMProvider, ProviderError

API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "deepseek/deepseek-chat"


class OpenRouterProvider(LLMProvider):
    name = "openrouter"
    label = "OpenRouter (hosted)"
    models = [
        "deepseek/deepseek-chat",
        "deepseek/deepseek-r1",
        "qwen/qwen-2.5-72b-instruct",
        "meta-llama/llama-3.1-70b-instruct",
        "google/gemini-2.0-flash-001",
    ]

    def __init__(self, model: str | None = None, timeout: int = 180):
        self.api_key = os.environ.get("OPENROUTER_API_KEY", "")
        self.model = model or os.environ.get("OPENROUTER_MODEL") or DEFAULT_MODEL
        self.timeout = timeout

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise ProviderError(self.setup_hint())
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": "Interview Prep Mapper",
        }
        payload = {"model": self.model, "messages": [{"role": "user", "content": prompt}]}
        try:
            resp = httpx.post(API_URL, headers=headers, json=payload, timeout=self.timeout)
        except httpx.HTTPError as exc:
            raise ProviderError(f"OpenRouter request failed: {exc}") from exc
        if resp.status_code != 200:
            # Error bodies carry an OpenRouter message, never the API key.
            raise ProviderError(f"OpenRouter returned {resp.status_code}: {resp.text[:500]}")
        try:
            content = resp.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"Unexpected OpenRouter response shape: {exc}") from exc
        content = (content or "").strip()
        if not content:
            raise ProviderError("OpenRouter returned an empty response")
        return content

    def setup_hint(self) -> str:
        return (
            "OpenRouter not configured. Create a key at https://openrouter.ai/keys, "
            "then set it before starting the server: "
            "`export OPENROUTER_API_KEY=sk-or-...`. Optionally set OPENROUTER_MODEL "
            f"(default: {DEFAULT_MODEL})."
        )
