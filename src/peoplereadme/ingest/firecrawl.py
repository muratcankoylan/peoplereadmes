"""Firecrawl ingestion: single-page scrape and async site crawl."""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime

import httpx

from ..evidence import EvidenceItem

API = "https://api.firecrawl.dev/v1"


def _client(client: httpx.Client | None) -> httpx.Client:
    if client is not None:
        return client
    key = os.environ.get("FIRECRAWL_API_KEY")
    if not key:
        raise ValueError("Set FIRECRAWL_API_KEY to ingest Firecrawl pages.")
    return httpx.Client(
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
        timeout=30,
    )


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _page_timestamp(metadata: dict) -> str:
    for key in (
        "publishedDate",
        "modifiedDate",
        "published_date",
        "modified_date",
        "datePublished",
        "dateModified",
    ):
        value = metadata.get(key)
        if value:
            return value
    return _now_iso()


def _page_url(metadata: dict, fallback_url: str) -> str:
    return metadata.get("sourceURL") or metadata.get("url") or fallback_url


def _normalize_page(page: dict, fallback_url: str, tier: str) -> EvidenceItem:
    metadata = page.get("metadata") or {}
    return EvidenceItem(
        source="firecrawl",
        url=_page_url(metadata, page.get("url") or fallback_url),
        timestamp=_page_timestamp(metadata),
        content=page.get("markdown") or "",
        kind="article",
        tier=tier,
        extra={
            "title": metadata.get("title") or "",
            "metadata": metadata,
        },
    )


def _scrape_payload(client: httpx.Client, url: str) -> dict:
    resp = client.post(
        f"{API}/scrape",
        json={"url": url, "formats": ["markdown"]},
    )
    resp.raise_for_status()
    return resp.json().get("data", {})


def ingest_firecrawl(
    url: str,
    client: httpx.Client | None = None,
    tier: str = "press",
) -> tuple[list[EvidenceItem], str]:
    """Returns (items, cursor). Cursor is the newest item timestamp seen."""
    owns_client = client is None
    client = _client(client)
    try:
        page = _scrape_payload(client, url)
        items = [_normalize_page(page, url, tier)]
    finally:
        if owns_client:
            client.close()
    cursor = items[-1].timestamp if items else ""
    return items, cursor


def crawl_firecrawl(
    url: str,
    client: httpx.Client | None = None,
    tier: str = "press",
    limit: int = 10,
    poll_interval: float = 2.0,
    timeout: float = 300.0,
) -> tuple[list[EvidenceItem], str]:
    """Submit a Firecrawl crawl job and poll until done. Returns (items, cursor)."""
    owns_client = client is None
    client = _client(client)
    try:
        resp = client.post(
            f"{API}/crawl",
            json={"url": url, "limit": limit, "scrapeOptions": {"formats": ["markdown"]}},
        )
        resp.raise_for_status()
        job = resp.json()
        job_id = job.get("id")
        if not job_id:
            raise ValueError(f"Firecrawl crawl returned no job id: {job!r}")

        deadline = time.monotonic() + timeout
        pages: list[dict] = []
        while True:
            status_resp = client.get(f"{API}/crawl/{job_id}")
            status_resp.raise_for_status()
            payload = status_resp.json()
            status = payload.get("status")
            if status == "completed":
                pages = payload.get("data") or []
                break
            if status in ("failed", "cancelled"):
                raise ValueError(f"Firecrawl crawl {job_id} {status}")
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Firecrawl crawl {job_id} did not complete within {timeout}s"
                )
            time.sleep(poll_interval)

        items = [
            _normalize_page(page, url, tier)
            for page in pages
            if (page.get("markdown") or "").strip()
        ]
    finally:
        if owns_client:
            client.close()
    items.sort(key=lambda i: i.timestamp)
    cursor = items[-1].timestamp if items else ""
    return items, cursor
