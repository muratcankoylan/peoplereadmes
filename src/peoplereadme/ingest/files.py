"""Arbitrary markdown / JSON file drops (talk transcripts, newsletters, notes)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ..evidence import EvidenceItem


def ingest_file(path: Path, kind: str = "article") -> tuple[list[EvidenceItem], str]:
    """Returns (items, cursor). One evidence item per file; timestamp from mtime."""
    timestamp = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()
    item = EvidenceItem(
        source="file",
        url=path.resolve().as_uri(),
        timestamp=timestamp,
        content=path.read_text(),
        kind=kind,
        extra={"filename": path.name},
    )
    return [item], timestamp
