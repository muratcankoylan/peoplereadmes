"""Repo discovery helpers."""

from __future__ import annotations

import json
from pathlib import Path

SCHEMA_RELPATH = Path("schemas") / "persona.schema.json"
MANIFEST_RELPATH = Path("manifest.json")


def find_repo_root(start: Path | None = None) -> Path:
    """Walk upward from `start` (default: cwd) to the directory holding manifest.json."""
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / MANIFEST_RELPATH).is_file() and (candidate / SCHEMA_RELPATH).is_file():
            return candidate
    raise FileNotFoundError(
        "Not inside a peoplereadmes repo (no manifest.json + schemas/persona.schema.json found)."
    )


def load_schema(root: Path) -> dict:
    return json.loads((root / SCHEMA_RELPATH).read_text())


def load_manifest(root: Path) -> dict:
    return json.loads((root / MANIFEST_RELPATH).read_text())


def save_manifest(root: Path, manifest: dict) -> None:
    (root / MANIFEST_RELPATH).write_text(json.dumps(manifest, indent=2) + "\n")
