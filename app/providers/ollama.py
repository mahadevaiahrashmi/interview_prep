"""Ollama provider — the fully open-source engine.

Shells out to the local `ollama` CLI, feeding the prompt on stdin so prompt
length and quoting are never an issue. Install: https://ollama.com, then pull a
model, e.g. `ollama pull llama3.1` or `ollama pull qwen2.5`.

Config via environment:
  OLLAMA_CMD    binary name (default: "ollama")
  OLLAMA_MODEL  model to run (default: "llama3.1")
"""
from __future__ import annotations

import os
import subprocess

from .base import LLMProvider, cli_exists, run_cli

DEFAULT_MODEL = "llama3.1"


class OllamaProvider(LLMProvider):
    name = "ollama"
    label = "Ollama (open source)"
    models = ["llama3.1", "qwen2.5", "mistral", "gemma2"]

    def __init__(self, model: str | None = None, timeout: int = 300):
        self.cmd = os.environ.get("OLLAMA_CMD", "ollama")
        self.model = model or os.environ.get("OLLAMA_MODEL") or DEFAULT_MODEL
        self.timeout = timeout

    def is_available(self) -> bool:
        return cli_exists(self.cmd)

    def installed_models(self) -> list[str]:
        if not self.is_available():
            return []
        try:
            proc = subprocess.run(
                [self.cmd, "list"], capture_output=True, text=True, timeout=15
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return []
        models = []
        for line in proc.stdout.splitlines()[1:]:  # skip header
            parts = line.split()
            if parts:
                models.append(parts[0])
        return models

    def suggested_models(self) -> list[str]:
        # Prefer the user's actually-installed models; fall back to suggestions.
        return self.installed_models() or list(self.models)

    def generate(self, prompt: str) -> str:
        # `ollama run MODEL` reads the prompt from stdin and prints the completion.
        return run_cli([self.cmd, "run", self.model], prompt, timeout=self.timeout)

    def setup_hint(self) -> str:
        return (
            "Ollama not found. Install from https://ollama.com, then pull a model "
            "with `ollama pull llama3.1` (or `qwen2.5`) and retry."
        )
