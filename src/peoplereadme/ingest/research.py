"""Research discovery primitives that return candidate URLs."""

from __future__ import annotations

import os

import httpx

PARALLEL_API = "https://api.parallel.ai/v1/search"
EXA_API = "https://api.exa.ai/search"


def _client(client: httpx.Client | None) -> httpx.Client:
    if client is not None:
        return client
    return httpx.Client(timeout=30)


def _urls_from_results(results: list[dict], limit: int) -> list[str]:
    urls: list[str] = []
    for result in results:
        url = result.get("url")
        if url:
            urls.append(url)
        if len(urls) >= limit:
            break
    return urls


def _discover_parallel(client: httpx.Client, query: str, limit: int) -> list[str]:
    key = os.environ.get("PARALLEL_API_KEY")
    if not key:
        raise ValueError("Set PARALLEL_API_KEY or EXA_API_KEY to discover sources.")
    resp = client.post(
        PARALLEL_API,
        headers={"x-api-key": key},
        json={
            "objective": query,
            "search_queries": [query],
            "advanced_settings": {"max_results": limit},
        },
    )
    resp.raise_for_status()
    return _urls_from_results(resp.json().get("results", []), limit)


def _discover_exa(client: httpx.Client, query: str, limit: int) -> list[str]:
    key = os.environ.get("EXA_API_KEY")
    if not key:
        raise ValueError("Set PARALLEL_API_KEY or EXA_API_KEY to discover sources.")
    resp = client.post(
        EXA_API,
        headers={"x-api-key": key},
        json={"query": query, "numResults": limit},
    )
    resp.raise_for_status()
    return _urls_from_results(resp.json().get("results", []), limit)


def discover_sources(
    query: str,
    *,
    client: httpx.Client | None = None,
    limit: int = 10,
) -> list[str]:
    """Return candidate source URLs from Parallel or Exa."""
    owns_client = client is None
    client = _client(client)
    try:
        if os.environ.get("PARALLEL_API_KEY"):
            return _discover_parallel(client, query, limit)
        if os.environ.get("EXA_API_KEY"):
            return _discover_exa(client, query, limit)
        raise ValueError("Set PARALLEL_API_KEY or EXA_API_KEY to discover sources.")
    finally:
        if owns_client:
            client.close()
