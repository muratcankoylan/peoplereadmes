"""Ingestion sources: X archive, GitHub, RSS, file drops."""

from pathlib import Path

from ..evidence import EvidenceItem
from .enrich import enrich
from .files import ingest_file
from .firecrawl import crawl_firecrawl, ingest_firecrawl
from .github import ingest_github
from .research import discover_sources
from .rss import ingest_rss
from .x_archive import ingest_x_archive
from .xapi import ingest_x_api

# Source kinds that can be re-polled unattended (no local file paths involved).
WATCHABLE_KINDS = ("x-api", "github", "rss")


def run_source(spec: str) -> tuple[list[EvidenceItem], str]:
    """Dispatch a `kind=value` source spec to its ingester; shared by ingest and watch."""
    kind, _, value = spec.partition("=")
    if not value:
        raise ValueError(f"invalid source spec {spec!r} (expected key=value)")
    if kind == "x-archive":
        return ingest_x_archive(Path(value))
    if kind == "x-api":
        return ingest_x_api(value)
    if kind == "github":
        return ingest_github(value)
    if kind == "rss":
        return ingest_rss(value)
    if kind == "firecrawl":
        return ingest_firecrawl(value)
    if kind == "firecrawl-crawl":
        return crawl_firecrawl(value)
    if kind == "file":
        return ingest_file(Path(value))
    raise ValueError(f"unknown source kind {kind!r}")


__all__ = [
    "WATCHABLE_KINDS",
    "crawl_firecrawl",
    "discover_sources",
    "enrich",
    "ingest_file",
    "ingest_firecrawl",
    "ingest_github",
    "ingest_rss",
    "ingest_x_api",
    "ingest_x_archive",
    "run_source",
]
