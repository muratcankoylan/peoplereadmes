"""Normalized evidence storage: evidence/{source}.jsonl + sources.lock.

Every ingested item is normalized to {source, url, timestamp, content, kind, hash}
(plus optional `extra` metadata used by trace extraction). Ingestion is incremental
and re-runnable: items are deduplicated by content hash and sources.lock records
per-source cursors, item counts, and a merkle root over item hashes.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    source: str
    url: str
    timestamp: str
    content: str
    kind: str
    hash: str = ""
    extra: dict = Field(default_factory=dict)

    def with_hash(self) -> EvidenceItem:
        if self.hash:
            return self
        digest = hashlib.sha256(
            f"{self.source}\n{self.url}\n{self.timestamp}\n{self.content}".encode()
        ).hexdigest()
        return self.model_copy(update={"hash": f"sha256:{digest}"})


def evidence_dir(persona_dir: Path) -> Path:
    return persona_dir / "evidence"


def _lock_path(persona_dir: Path) -> Path:
    return evidence_dir(persona_dir) / "sources.lock"


def load_sources_lock(persona_dir: Path) -> dict:
    path = _lock_path(persona_dir)
    if path.is_file():
        return json.loads(path.read_text())
    return {"sources": {}}


def save_sources_lock(persona_dir: Path, lock: dict) -> None:
    _lock_path(persona_dir).write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")


def load_evidence(persona_dir: Path, source: str | None = None) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    directory = evidence_dir(persona_dir)
    if not directory.is_dir():
        return items
    paths = (
        [directory / f"{source}.jsonl"]
        if source
        else sorted(directory.glob("*.jsonl"))
    )
    for path in paths:
        if not path.is_file():
            continue
        for line in path.read_text().splitlines():
            if line.strip():
                items.append(EvidenceItem.model_validate_json(line))
    return items


def merkle_root(hashes: list[str]) -> str:
    digest = hashlib.sha256("\n".join(sorted(hashes)).encode()).hexdigest()
    return f"sha256:{digest}"


def append_evidence(
    persona_dir: Path,
    source: str,
    items: list[EvidenceItem],
    cursor: str | None = None,
) -> int:
    """Append new (deduplicated) items to evidence/{source}.jsonl. Returns count added."""
    directory = evidence_dir(persona_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{source}.jsonl"

    existing_hashes = {item.hash for item in load_evidence(persona_dir, source)}
    new_items = []
    for item in items:
        hashed = item.with_hash()
        if hashed.hash not in existing_hashes:
            existing_hashes.add(hashed.hash)
            new_items.append(hashed)

    if new_items:
        with path.open("a") as fh:
            for item in new_items:
                fh.write(item.model_dump_json() + "\n")

    lock = load_sources_lock(persona_dir)
    all_hashes = [item.hash for item in load_evidence(persona_dir, source)]
    entry = lock["sources"].setdefault(source, {})
    entry["item_count"] = len(all_hashes)
    entry["merkle_root"] = merkle_root(all_hashes)
    if cursor is not None:
        entry["last_cursor"] = cursor
    save_sources_lock(persona_dir, lock)
    return len(new_items)
