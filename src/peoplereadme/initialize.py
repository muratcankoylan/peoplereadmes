"""`peoplereadme init`: create a schema-valid persona package skeleton."""

from __future__ import annotations

import json
from pathlib import Path

from .models import (
    Consent,
    Heuristic,
    IdentityBoundary,
    PersonaClass,
    PersonaManifest,
    Project,
    Safety,
)
from .repo import find_repo_root, load_manifest, save_manifest

NON_AFFILIATION_HEADER = (
    "This package models public professional patterns only. It is not affiliated "
    "with, endorsed by, or speaking as the subject. Third-person pattern analysis only."
)

SELF_EXPORTS = [
    "idea_engine",
    "taste_filter",
    "scope_cut",
    "project_review",
    "voice",
    "decision_sim",
]
OTHER_EXPORTS = ["idea_engine", "taste_filter", "scope_cut", "project_review", "decision_sim"]

DIRS = [
    "context",
    "data",
    "prompts",
    "evals/rubrics",
    "evals/fidelity",
    "research",
    "evidence",
    "traces",
    "compiled",
    "exports",
    "examples",
]


def _placeholder_persona(persona_id: str, persona_class: PersonaClass) -> PersonaManifest:
    display = persona_id.replace("-", " ").title()
    if persona_class is PersonaClass.SELF:
        allowed = [
            "first-person drafting with consent",
            "ideation and review in the subject's own workflows",
        ]
        consent: Consent | None = Consent(
            granted_by=persona_id, date="", scope="self-compile; full export set"
        )
        exports = SELF_EXPORTS
    else:
        allowed = [
            "third-person pattern analysis",
            "review and ideation inspired by public work",
        ]
        consent = None
        exports = OTHER_EXPORTS
    return PersonaManifest(
        id=persona_id,
        name=display,
        scope=(
            f"Public professional patterns of {display}. "
            "Does not cover private psychology, relationships, or private communications."
        ),
        persona_class=persona_class,
        consent=consent,
        allowed_exports=exports,
        identity_boundary=IdentityBoundary(
            allowed=allowed,
            disallowed=[
                "first-person impersonation without consent",
                "private inference",
                "doxxing or harassment workflows",
                "real-time tracking",
                "biometric or social scoring",
            ],
        ),
        projects=[
            Project(
                name="placeholder-project",
                category="placeholder",
                data_source="public sources only (replace)",
                method_summary="Replace with a high-level method statement.",
                risk_notes=["replace with real risk notes"],
            )
        ],
        heuristics=[
            Heuristic(
                id="placeholder-heuristic",
                name="Placeholder heuristic",
                description="Replace with an evidence-backed heuristic.",
            )
        ],
        safety=Safety(
            required_defaults=[
                "evidence-bound claims only",
                "non-impersonation framing" if persona_class is PersonaClass.OTHER
                else "consent-scoped generation only",
            ],
            refusal_categories=[
                "private inference",
                "harassment or doxxing",
                "credential misuse or access-control bypass",
            ],
        ),
    )


def _write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=2) + "\n")


def init_persona(persona_id: str, persona_class: PersonaClass, root: Path | None = None) -> Path:
    """Create personas/{id}/ skeleton and register it in manifest.json."""
    root = root or find_repo_root()
    persona_dir = root / "personas" / persona_id
    if persona_dir.exists():
        raise FileExistsError(f"personas/{persona_id}/ already exists")

    for d in DIRS:
        (persona_dir / d).mkdir(parents=True)

    persona = _placeholder_persona(persona_id, persona_class)
    _write_json(persona_dir / "persona.json", persona.model_dump_persona())

    boundary_note = "" if persona_class is PersonaClass.SELF else f"\n> {NON_AFFILIATION_HEADER}\n"
    (persona_dir / "README.md").write_text(
        f"# {persona.name} ({persona_class.value}-persona)\n{boundary_note}\n"
        "Load order:\n\n"
        "1. `context/context-pack.md`\n"
        "2. `prompts/system-prompt.md`\n"
        "3. `context/safety-boundaries.md`\n\n"
        "Machine layers: `evidence/`, `traces/`, `compiled/`, `exports/`, `persona.lock`.\n"
    )
    (persona_dir / "context" / "context-pack.md").write_text(
        f"# {persona.name} Context Pack\n\nCompact default context. Replace with synthesis.\n"
    )
    (persona_dir / "context" / "safety-boundaries.md").write_text(
        f"# Safety Boundaries\n\n{NON_AFFILIATION_HEADER}\n"
        if persona_class is PersonaClass.OTHER
        else "# Safety Boundaries\n\nConsented self-persona. Generation is scoped by "
        "`consent` and `allowed_exports` in `persona.json`.\n"
    )
    (persona_dir / "prompts" / "system-prompt.md").write_text(
        f"# System Prompt: {persona.name}\n\nReplace with agent instructions.\n"
    )
    (persona_dir / "prompts" / "task-modes.md").write_text(
        "# Task Modes\n\nReplace with task mode definitions.\n"
    )
    (persona_dir / "evals" / "rubric.md").write_text(
        "# Rubric\n\nReplace with evaluation rubric. Codified versions live in "
        "`evals/rubrics/v{N}.json`.\n"
    )
    _write_json(
        persona_dir / "data" / "projects.json",
        {"persona_id": persona_id, "projects": []},
    )
    _write_json(
        persona_dir / "data" / "sources.json",
        {"persona_id": persona_id, "sources": []},
    )
    _write_json(
        persona_dir / "data" / "heuristics.json",
        {"persona_id": persona_id, "heuristics": []},
    )
    _write_json(persona_dir / "evidence" / "sources.lock", {"sources": {}})
    _write_json(persona_dir / "traces" / "splits.json", {"splits": {}})
    if persona_class is PersonaClass.SELF:
        (persona_dir / "evidence" / ".gitignore").write_text(
            "# Self-persona evidence stays local-only; sources.lock (hashes, counts) is "
            "committed.\n*.jsonl\n"
        )
    for d in ("research", "compiled", "exports", "examples"):
        (persona_dir / d / ".gitkeep").write_text("")

    manifest = load_manifest(root)
    entry = {
        "id": persona_id,
        "name": persona.name,
        "class": persona_class.value,
        "status": "skeleton",
        "entrypoint": f"personas/{persona_id}/README.md",
        "persona": f"personas/{persona_id}/persona.json",
        "default_context": f"personas/{persona_id}/context/context-pack.md",
        "system_prompt": f"personas/{persona_id}/prompts/system-prompt.md",
    }
    manifest.setdefault("personas", []).append(entry)
    save_manifest(root, manifest)
    return persona_dir
