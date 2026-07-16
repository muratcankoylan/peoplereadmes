"""Format-agnostic export bundle (PRD 11 / M4).

Everything an export format needs, assembled once from the persona package:
identity + boundary metadata from persona.json, the bounded persona brief, the
capability prompt set gated by `allowed_exports`, and — when a compiled program
exists — the GEPA-optimized draft/refine instructions with their provenance
from compile.lock.json. Other-personas always carry the non-affiliation header
and never export the `voice` capability.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, Field

from ..compiler.program import persona_brief
from ..initialize import NON_AFFILIATION_HEADER

CAPABILITY_PROMPTS = {
    "idea_engine": (
        "Generate project or content ideas the way this person would: apply their "
        "selection heuristics, favor their recurring domains and data seams, and "
        "discard ideas they would reject. State each idea the way they would pitch it."
    ),
    "taste_filter": (
        "Critique or rewrite a draft using this person's taste: cut what they would "
        "cut, keep their specificity and opinions, match their typical length, casing, "
        "and formatting. Point at concrete tells, not generic style advice."
    ),
    "scope_cut": (
        "Cut a project scope the way this person would: identify the smallest "
        "shippable core, remove everything they would defer, and justify each cut "
        "with their own heuristics."
    ),
    "project_review": (
        "Review a project, PR, or plan the way this person would: their standards, "
        "their pet concerns, their tolerance for risk and shortcuts. Verdict first, "
        "then the reasons they would actually give."
    ),
    "voice": (
        "Write the artifact in this person's voice: their diction, rhythm, casing, "
        "length, and formatting, indistinguishable from their real writing."
    ),
    "decision_sim": (
        "Simulate the decision this person would make: state the decision, then the "
        "rationale in terms of their documented heuristics and past behavior. Flag "
        "where the evidence is thin instead of inventing conviction."
    ),
}


class CompiledInstructions(BaseModel):
    draft: str
    refine: str
    provenance: dict = Field(default_factory=dict)


class ExportBundle(BaseModel):
    persona_id: str
    name: str
    persona_class: str
    scope: str
    non_affiliation: str | None = None
    capabilities: dict[str, str]
    brief: str
    brief_hash: str
    compiled: CompiledInstructions | None = None
    disallowed: list[str] = Field(default_factory=list)


def _load_compiled(persona_dir: Path) -> CompiledInstructions | None:
    program_path = persona_dir / "compiled" / "program.json"
    if not program_path.is_file():
        return None
    state = json.loads(program_path.read_text())
    try:
        draft = state["draft"]["signature"]["instructions"]
        refine = state["refine"]["signature"]["instructions"]
    except (KeyError, TypeError):
        return None
    provenance = {}
    lock_path = persona_dir / "compiled" / "compile.lock.json"
    if lock_path.is_file():
        lock = json.loads(lock_path.read_text())
        provenance = {
            k: lock[k]
            for k in (
                "optimizer",
                "task_model",
                "reflection_model",
                "dataset_hash",
                "seed_dev_score",
                "compiled_dev_score",
                "timestamp",
            )
            if k in lock
        }
    return CompiledInstructions(draft=draft, refine=refine, provenance=provenance)


def build_bundle(persona_dir: Path, persona_id: str) -> ExportBundle:
    """Assemble the export bundle; enforces allowed_exports and class gating."""
    persona_path = persona_dir / "persona.json"
    if not persona_path.is_file():
        raise FileNotFoundError(f"{persona_path} not found (run `peoplereadme init` first)")
    persona = json.loads(persona_path.read_text())
    persona_class = persona.get("class", "other")
    allowed = persona.get("allowed_exports", [])
    if persona_class != "self":
        allowed = [c for c in allowed if c != "voice"]
    capabilities = {c: CAPABILITY_PROMPTS[c] for c in allowed if c in CAPABILITY_PROMPTS}
    if not capabilities:
        raise ValueError(
            f"persona {persona_id!r} has no exportable capabilities "
            "(check `allowed_exports` in persona.json)"
        )
    brief = persona_brief(persona_dir)
    return ExportBundle(
        persona_id=persona_id,
        name=persona.get("name", persona_id),
        persona_class=persona_class,
        scope=persona.get("scope", ""),
        non_affiliation=NON_AFFILIATION_HEADER if persona_class != "self" else None,
        capabilities=capabilities,
        brief=brief,
        brief_hash=f"sha256:{hashlib.sha256(brief.encode()).hexdigest()}",
        compiled=_load_compiled(persona_dir),
        disallowed=persona.get("identity_boundary", {}).get("disallowed", []),
    )
