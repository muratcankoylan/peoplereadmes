"""Validate persona packages against schemas/persona.schema.json."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

from .repo import find_repo_root, load_schema


def validate_persona_object(obj: dict, root: Path | None = None) -> list[str]:
    """Validate a persona object. Returns a list of error messages (empty = valid)."""
    root = root or find_repo_root()
    validator = jsonschema.Draft202012Validator(load_schema(root))
    return [
        f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
        for e in validator.iter_errors(obj)
    ]


def validate_persona_dir(persona_dir: Path, root: Path | None = None) -> list[str]:
    """Validate personas/{id}/persona.json if present."""
    persona_json = persona_dir / "persona.json"
    if not persona_json.is_file():
        return [f"{persona_json} not found"]
    return validate_persona_object(json.loads(persona_json.read_text()), root=root)


def validate_all(root: Path | None = None) -> dict[str, list[str]]:
    """Validate every persona that ships a persona.json. Legacy packages without one are
    skipped (the schema change is additive, so they remain valid)."""
    root = root or find_repo_root()
    results: dict[str, list[str]] = {}
    personas_dir = root / "personas"
    if not personas_dir.is_dir():
        return results
    for persona_dir in sorted(personas_dir.iterdir()):
        if (persona_dir / "persona.json").is_file():
            results[persona_dir.name] = validate_persona_dir(persona_dir, root=root)
    return results
