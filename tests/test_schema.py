"""Schema change is additive: pre-existing persona objects stay valid unchanged."""

import json
from pathlib import Path

from peoplereadme.validate import validate_persona_object

REPO_ROOT = Path(__file__).resolve().parents[1]
RILEY = REPO_ROOT / "personas" / "riley-walz" / "data"

LEGACY_PERSONA = {
    "id": "legacy",
    "name": "Legacy Person",
    "scope": "Public patterns only.",
    "identity_boundary": {"allowed": ["analysis"], "disallowed": ["impersonation"]},
    "projects": [],
    "heuristics": [],
    "safety": {"required_defaults": ["evidence-bound"], "refusal_categories": ["doxxing"]},
}


def test_legacy_persona_without_new_fields_validates():
    assert validate_persona_object(LEGACY_PERSONA, root=REPO_ROOT) == []


def test_riley_package_data_validates_under_new_schema():
    """Assemble a persona object from the unchanged Riley data files and validate it."""
    projects = json.loads((RILEY / "projects.json").read_text())["projects"]
    heuristics = json.loads((RILEY / "heuristics.json").read_text())["heuristics"]
    persona = dict(
        LEGACY_PERSONA,
        id="riley-walz",
        name="Riley Walz",
        projects=projects,
        heuristics=heuristics,
    )
    assert validate_persona_object(persona, root=REPO_ROOT) == []


def test_new_fields_validate():
    persona = dict(
        LEGACY_PERSONA,
        **{
            "class": "self",
            "consent": {"granted_by": "legacy", "date": "2026-06-11", "scope": "self-compile"},
            "allowed_exports": ["voice", "idea_engine"],
        },
    )
    assert validate_persona_object(persona, root=REPO_ROOT) == []


def test_invalid_class_rejected():
    persona = dict(LEGACY_PERSONA, **{"class": "fan-fiction"})
    assert validate_persona_object(persona, root=REPO_ROOT) != []
