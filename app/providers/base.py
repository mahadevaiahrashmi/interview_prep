"""Provider interface and a shared subprocess helper.

Every provider turns a single prompt string into a raw text response. Real
providers (Claude/Gemini/Ollama CLIs) shell out to their CLI; the mock provider
returns a deterministic response for offline use and tests.
"""
from __future__ import annotations

import shutil
import subprocess
from abc import ABC, abstractmethod


class ProviderError(RuntimeError):
    """Raised when a provider is unavailable or its CLI call fails."""


class LLMProvider(ABC):
    name: str = "base"
    label: str = "Base"
    models: list[str] = []

    @abstractmethod
    def is_available(self) -> bool:
        """True if this provider can run on the current machine."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Return the model's raw text response for `prompt`."""

    def setup_hint(self) -> str:
        """Human-readable install/setup instructions, shown when unavailable."""
        return ""

    def suggested_models(self) -> list[str]:
        """Model ids to offer in the UI dropdown; empty means default-only."""
        return list(self.models)


def cli_exists(binary: str) -> bool:
    return shutil.which(binary) is not None


def run_cli(cmd: list[str], prompt: str, timeout: int = 180) -> str:
    """Run `cmd`, feeding `prompt` on stdin, and return stdout.

    Raises ProviderError on missing binary, timeout, or non-zero exit.
    """
    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise ProviderError(f"Command not found: {cmd[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ProviderError(f"{cmd[0]} timed out after {timeout}s") from exc

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        raise ProviderError(f"{cmd[0]} exited {proc.returncode}: {stderr[:500]}")

    out = (proc.stdout or "").strip()
    if not out:
        raise ProviderError(f"{cmd[0]} returned an empty response")
    return out
