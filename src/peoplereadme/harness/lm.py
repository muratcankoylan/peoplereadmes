"""LM access for the harness.

A minimal Protocol so tests inject fakes; production path goes through litellm
(PRD 12). Judge calls are deterministic (temperature 0) and disk-cached in
~/.peoplereadme/cache/llm (PRD 16: cached judge calls) keyed by a content hash.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Protocol


class LMError(RuntimeError):
    """Provider/model call failure surfaced as a clean CLI error."""


class LM(Protocol):
    model: str

    def complete(self, system: str, user: str) -> str: ...


class LiteLLM:
    """litellm-backed LM. Imported lazily so offline tests never touch it."""

    def __init__(self, model: str, temperature: float = 0.0, max_tokens: int = 1024):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def complete(self, system: str, user: str) -> str:
        import litellm

        try:
            response = litellm.completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        except Exception as exc:
            raise LMError(f"model call failed ({self.model}): {exc}") from exc
        return response.choices[0].message.content or ""


def _cache_dir() -> Path:
    return Path(os.environ.get("PEOPLEREADME_CACHE", Path.home() / ".peoplereadme")) / (
        "cache/llm"
    )


class CachedLM:
    """Disk cache wrapper; safe for deterministic (temperature 0) calls."""

    def __init__(self, inner: LM):
        self.inner = inner
        self.model = inner.model

    def complete(self, system: str, user: str) -> str:
        key = hashlib.sha256(f"{self.model}\x00{system}\x00{user}".encode()).hexdigest()
        path = _cache_dir() / f"{key}.json"
        if path.is_file():
            return json.loads(path.read_text())["output"]
        output = self.inner.complete(system, user)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"model": self.model, "output": output}))
        return output


def build_lm(model: str, temperature: float = 0.0, cached: bool = True) -> LM:
    lm: LM = LiteLLM(model, temperature=temperature)
    return CachedLM(lm) if cached and temperature == 0.0 else lm


def extract_json(text: str) -> dict:
    """Pull the first JSON object out of a model response (handles code fences)."""
    start = text.find("{")
    if start == -1:
        raise ValueError(f"no JSON object in response: {text[:200]!r}")
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError(f"unbalanced JSON in response: {text[:200]!r}")
