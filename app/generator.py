"""Orchestration: JD -> prompt -> provider -> validated PrepPlan.

Models don't always return clean JSON, so `extract_json` is defensive: it strips
code fences and isolates the first balanced JSON object before parsing.
"""
from __future__ import annotations

import json
import re

from pydantic import ValidationError

from .prompts import build_prompt
from .providers import ProviderError, get_provider
from .schema import PrepPlan


class GenerationError(RuntimeError):
    """Raised when the model output can't be turned into a valid PrepPlan."""


def extract_json(raw: str) -> str:
    """Isolate the first balanced JSON object in `raw`.

    Handles ```json fences and leading/trailing prose by scanning for the first
    '{' and counting brace depth (ignoring braces inside strings).
    """
    text = raw.strip()
    if text.startswith("```"):
        # Drop the opening fence line (``` or ```json) and any closing fence.
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    start = text.find("{")
    if start == -1:
        raise GenerationError("No JSON object found in model output.")

    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise GenerationError("Unbalanced JSON braces in model output.")


def _scrub_controls(obj):
    """Strip XML/CSV-hostile control chars from every string in a parsed tree.

    Local models sometimes embed raw control characters (or literal newlines) in
    string values. They parse fine but break table rendering, so we fold
    whitespace to spaces and drop the rest.
    """
    if isinstance(obj, str):
        s = obj.replace("\t", " ").replace("\r", " ").replace("\n", " ")
        return "".join(ch for ch in s if ch >= " ")
    if isinstance(obj, list):
        return [_scrub_controls(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _scrub_controls(v) for k, v in obj.items()}
    return obj


def _repair_json(snippet: str) -> str:
    """Best-effort fixes for the JSON mistakes instruct models commonly make.

    Conservative on purpose: only normalises curly double-quotes to straight ones
    and drops trailing commas before a closing brace/bracket. Both are frequent
    and unambiguous; riskier rewrites are left alone so we never silently corrupt
    the output.
    """
    s = snippet.replace("“", '"').replace("”", '"')
    s = re.sub(r",(\s*[}\]])", r"\1", s)
    return s


def parse_plan(raw: str) -> PrepPlan:
    snippet = extract_json(raw)
    try:
        # strict=False tolerates literal newlines/tabs inside string values,
        # which local models (e.g. via Ollama) routinely emit unescaped.
        data = json.loads(snippet, strict=False)
    except json.JSONDecodeError:
        try:
            data = json.loads(_repair_json(snippet), strict=False)
        except json.JSONDecodeError as exc:
            raise GenerationError(f"Model returned invalid JSON: {exc}") from exc
    data = _scrub_controls(data)
    try:
        plan = PrepPlan.model_validate(data)
    except ValidationError as exc:
        raise GenerationError(f"Model JSON did not match the schema: {exc}") from exc
    return plan.nonempty_rows()


_RETRY_SUFFIX = (
    "\n\nIMPORTANT: Your previous reply could not be parsed. Respond with ONLY one "
    "valid JSON object matching the schema — no prose, no markdown fences, no "
    "trailing commas."
)


def generate_plan(
    jd: str,
    provider_name: str = "mock",
    model: str | None = None,
    instructions: str = "",
    retries: int = 1,
) -> PrepPlan:
    if not jd.strip():
        raise GenerationError("Job description is empty.")

    provider = get_provider(provider_name, model)
    if not provider.is_available():
        raise GenerationError(provider.setup_hint() or f"Provider '{provider_name}' is unavailable.")

    prompt = build_prompt(jd, instructions)
    last_err: GenerationError | None = None
    for attempt in range(retries + 1):
        # On a retry, append a firm reminder to emit clean JSON.
        attempt_prompt = prompt if attempt == 0 else prompt + _RETRY_SUFFIX
        try:
            raw = provider.generate(attempt_prompt)
        except ProviderError as exc:
            raise GenerationError(str(exc)) from exc
        try:
            return parse_plan(raw)
        except GenerationError as exc:
            last_err = exc  # malformed JSON or schema mismatch — regenerate, then give up
    raise last_err
