"""Claude CLI provider.

Shells out to Anthropic's `claude` CLI (Claude Code) in non-interactive print
mode, feeding the prompt on stdin. Install:
`npm install -g @anthropic-ai/claude-code`, then run `claude` once to sign in.

Tools are disabled (`--tools ""`) so the call is a pure text completion — the
shelled-out model gets no file or shell access to the host running this server.

Config via environment:
  CLAUDE_CMD    binary name (default: "claude")
  CLAUDE_MODEL  optional model alias/id passed with --model (e.g. "sonnet", "opus")
"""
from __future__ import annotations

import os

from .base import LLMProvider, cli_exists, run_cli


class ClaudeCLIProvider(LLMProvider):
    name = "claude"
    label = "Claude CLI"
    models = ["sonnet", "opus", "haiku"]

    def __init__(self, model: str | None = None, timeout: int = 180):
        self.cmd = os.environ.get("CLAUDE_CMD", "claude")
        self.model = model or os.environ.get("CLAUDE_MODEL") or ""
        self.timeout = timeout

    def is_available(self) -> bool:
        return cli_exists(self.cmd)

    def generate(self, prompt: str) -> str:
        # -p: non-interactive print mode; the prompt arrives on stdin.
        argv = [self.cmd, "-p", "--output-format", "text", "--tools", ""]
        if self.model:
            argv += ["--model", self.model]
        return run_cli(argv, prompt, timeout=self.timeout)

    def setup_hint(self) -> str:
        return (
            "Claude CLI not found. Install it with "
            "`npm install -g @anthropic-ai/claude-code`, run `claude` once to "
            "sign in, then retry."
        )
