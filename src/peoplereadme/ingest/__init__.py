"""Ingestion sources: X archive, GitHub, RSS, file drops."""

from .enrich import enrich
from .files import ingest_file
from .firecrawl import crawl_firecrawl, ingest_firecrawl
from .github import ingest_github
from .research import discover_sources
from .rss import ingest_rss
from .x_archive import ingest_x_archive
from .xapi import ingest_x_api

__all__ = [
    "crawl_firecrawl",
    "discover_sources",
    "enrich",
    "ingest_file",
    "ingest_firecrawl",
    "ingest_github",
    "ingest_rss",
    "ingest_x_api",
    "ingest_x_archive",
]
