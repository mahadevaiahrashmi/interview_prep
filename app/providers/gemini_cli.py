"""Gemini CLI provider.

Shells out to Google's `gemini` CLI in non-interactive mode, feeding the prompt
on stdin. Install: https://github.com/google-gemini/gemini-cli
(`npm install -g @google/gemini-cli`), then authenticate per its docs.

Config via environment:
  GEMINI_CMD    binary name (default: "gemini")
  GEMINI_MODEL  optional model id passed with -m (e.g. "gemini-2.5-flash")
"""
from __future__ import annotations

import os

from .base import LLMProvider, cli_exists, run_cli


class GeminiCLIProvider(LLMProvider):
    name = "gemini"
    label = "Gemini CLI"
    models = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"]

    def __init__(self, model: str | None = None, timeout: int = 180):
        self.cmd = os.environ.get("GEMINI_CMD", "gemini")
        self.model = model or os.environ.get("GEMINI_MODEL") or ""
        self.timeout = timeout

    def is_available(self) -> bool:
        return cli_exists(self.cmd)

    def generate(self, prompt: str) -> str:
        argv = [self.cmd]
        if self.model:
            argv += ["-m", self.model]
        # Non-interactive: prompt arrives on stdin.
        return run_cli(argv, prompt, timeout=self.timeout)

    def setup_hint(self) -> str:
        return (
            "Gemini CLI not found. Install it with "
            "`npm install -g @google/gemini-cli`, run `gemini` once to sign in, "
            "then retry."
        )
