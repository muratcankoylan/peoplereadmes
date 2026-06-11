import json
from pathlib import Path

import pytest

from peoplereadme.initialize import init_persona
from peoplereadme.models import PersonaClass
from peoplereadme.repo import load_manifest
from peoplereadme.validate import validate_persona_dir

REQUIRED_FILES = [
    "README.md",
    "persona.json",
    "context/context-pack.md",
    "context/safety-boundaries.md",
    "prompts/system-prompt.md",
    "prompts/task-modes.md",
    "data/projects.json",
    "data/sources.json",
    "data/heuristics.json",
    "evals/rubric.md",
    "evidence/sources.lock",
    "traces/splits.json",
]


@pytest.mark.parametrize("persona_class", [PersonaClass.SELF, PersonaClass.OTHER])
def test_init_creates_schema_valid_skeleton(tmp_repo: Path, persona_class: PersonaClass):
    persona_dir = init_persona("test-person", persona_class, root=tmp_repo)
    for rel in REQUIRED_FILES:
        assert (persona_dir / rel).is_file(), rel
    assert validate_persona_dir(persona_dir, root=tmp_repo) == []

    persona = json.loads((persona_dir / "persona.json").read_text())
    assert persona["class"] == persona_class.value
    if persona_class is PersonaClass.SELF:
        assert "voice" in persona["allowed_exports"]
        assert (persona_dir / "evidence" / ".gitignore").is_file()
    else:
        assert "voice" not in persona["allowed_exports"]
        assert "consent" not in persona


def test_init_registers_manifest_entry(tmp_repo: Path):
    init_persona("test-person", PersonaClass.OTHER, root=tmp_repo)
    manifest = load_manifest(tmp_repo)
    entry = next(p for p in manifest["personas"] if p["id"] == "test-person")
    assert entry["class"] == "other"
    assert entry["persona"] == "personas/test-person/persona.json"


def test_init_refuses_existing_persona(tmp_repo: Path):
    init_persona("test-person", PersonaClass.OTHER, root=tmp_repo)
    with pytest.raises(FileExistsError):
        init_persona("test-person", PersonaClass.OTHER, root=tmp_repo)
