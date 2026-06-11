"""Ingestion sources: X archive, GitHub, RSS, file drops."""

from .files import ingest_file
from .github import ingest_github
from .rss import ingest_rss
from .x_archive import ingest_x_archive

__all__ = ["ingest_file", "ingest_github", "ingest_rss", "ingest_x_archive"]
