"""LM access for the harness.

A minimal Protocol so tests inject fakes; production path goes through litellm
(PRD 12). Judge calls are deterministic (temperature 0) and disk-cached in
~/.peoplereadme/cache/llm (PRD 16: cached judge calls) keyed by a content hash.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Protocol


class LMError(RuntimeError):
    """Provider/model call failure surfaced as a clean CLI error."""


def pmap[T, R](fn: Callable[[T], R], items: Sequence[T], max_workers: int = 1) -> list[R]:
    """Order-preserving parallel map; propagates the first exception raised."""
    if max_workers <= 1 or len(items) <= 1:
        return [fn(item) for item in items]
    with ThreadPoolExecutor(max_workers=min(max_workers, len(items))) as pool:
        return list(pool.map(fn, items))


class CostTracker:
    """Thread-safe accumulator for provider spend across a harness run."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.cost_usd = 0.0

    def reset(self) -> None:
        with self._lock:
            self.calls = 0
            self.prompt_tokens = 0
            self.completion_tokens = 0
            self.cost_usd = 0.0

    def record(self, prompt_tokens: int, completion_tokens: int, cost_usd: float) -> None:
        with self._lock:
            self.calls += 1
            self.prompt_tokens += prompt_tokens
            self.completion_tokens += completion_tokens
            self.cost_usd += cost_usd

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "lm_calls": self.calls,
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "cost_usd": round(self.cost_usd, 4),
            }


cost_tracker = CostTracker()


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

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        kwargs = {"temperature": self.temperature, "max_tokens": self.max_tokens}
        try:
            try:
                response = litellm.completion(model=self.model, messages=messages, **kwargs)
            except litellm.BadRequestError as exc:
                # Reasoning models (o-series, gpt-5.x) only accept the default
                # temperature; retry without it rather than failing the run.
                if "temperature" not in str(exc):
                    raise
                kwargs.pop("temperature")
                response = litellm.completion(model=self.model, messages=messages, **kwargs)
            content = response.choices[0].message.content
        except Exception as exc:
            raise LMError(f"model call failed ({self.model}): {exc}") from exc
        self._record_cost(response)
        return content or ""

    def _record_cost(self, response) -> None:
        import litellm

        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0
        try:
            cost = litellm.completion_cost(completion_response=response)
        except Exception:
            cost = 0.0
        cost_tracker.record(prompt_tokens, completion_tokens, cost)


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
