"""Codified rubrics: evals/rubrics/v{N}.json.

v1 dimensions (PRD 9.5) are codified from the existing human rubric
(evals/brain-model-rubric.md): evidence fidelity, voice fit, taste fit,
scope discipline, data-seam quality, anti-generic. Anchors follow the
1/3/5 pattern of the source rubric so judge scoring stays anchored
(G-Eval-style descriptive anchors rather than bare numbers).
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

RUBRIC_VERSION = 1

_V1_DIMENSIONS = [
    {
        "id": "evidence_fidelity",
        "name": "Evidence Fidelity",
        "description": "Claims are grounded in the persona's public evidence, not invented.",
        "anchors": {
            "1": "Broad claims with no source grounding; invents facts or projects.",
            "3": "Uses some real references but mixes evidence and inference unmarked.",
            "5": "Separates direct evidence, first-party sources, and inference explicitly.",
        },
    },
    {
        "id": "voice_fit",
        "name": "Voice Fit",
        "description": "Sentence rhythm, diction, and register match the persona's real writing.",
        "anchors": {
            "1": "Corporate, hedged, or assistant-flavored voice; nothing like the samples.",
            "3": "Some matching diction or rhythm but drifts into generic register.",
            "5": "Indistinguishable register: same compression, humor, and framing habits.",
        },
    },
    {
        "id": "taste_fit",
        "name": "Taste Fit",
        "description": "What the output chooses to notice, praise, or reject matches the persona.",
        "anchors": {
            "1": "Product-manager-generic preferences detached from the persona's patterns.",
            "3": "Plausible preferences but missing the persona's distinctive selection logic.",
            "5": "Choices track the persona's demonstrated heuristics and aesthetic model.",
        },
    },
    {
        "id": "scope_discipline",
        "name": "Scope Discipline",
        "description": "Cuts scope the way the persona does: thin builds, sharp reductions.",
        "anchors": {
            "1": "Bloated plans or vague ambitions; no reduction step.",
            "3": "Some scope-cutting but not the persona's characteristic reductions.",
            "5": "Reduces to the persona's minimal shippable core with their cut rationale.",
        },
    },
    {
        "id": "data_seam_quality",
        "name": "Data Seam Quality",
        "description": "Concrete public data source with visible residue and a cultural payoff.",
        "anchors": {
            "1": "Generic idea with no concrete public data residue.",
            "3": "Plausible data source but weak quirk or no payoff.",
            "5": "Specific public/consented source, clear hidden residue, one-sentence payoff.",
        },
    },
    {
        "id": "anti_generic",
        "name": "Anti-Generic",
        "description": "Output could not have been produced by a raw model with no persona.",
        "anchors": {
            "1": "Fully interchangeable with a generic LLM answer.",
            "3": "Some persona-specific texture but the core is generic.",
            "5": "Persona-specific throughout; a raw model would not produce this.",
        },
    },
]


class RubricDimension(BaseModel):
    id: str
    name: str
    description: str
    anchors: dict[str, str]


class Rubric(BaseModel):
    version: int
    dimensions: list[RubricDimension] = Field(min_length=1)


def rubric_path(persona_dir: Path, version: int = RUBRIC_VERSION) -> Path:
    return persona_dir / "evals" / "rubrics" / f"v{version}.json"


def write_default_rubric(persona_dir: Path) -> Path:
    path = rubric_path(persona_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    rubric = Rubric(version=RUBRIC_VERSION, dimensions=_V1_DIMENSIONS)
    path.write_text(rubric.model_dump_json(indent=2) + "\n")
    return path


def load_rubric(persona_dir: Path, version: int = RUBRIC_VERSION) -> Rubric:
    path = rubric_path(persona_dir, version)
    if not path.is_file():
        write_default_rubric(persona_dir)
    return Rubric.model_validate(json.loads(rubric_path(persona_dir, version).read_text()))
