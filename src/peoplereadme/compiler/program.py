"""The persona as a DSPy program (PRD 10).

Two-stage module: a draft predictor produces the artifact, a refine predictor
acts as the taste/voice filter that rewrites it to pass as the person. Both
signatures carry the persona brief (package files) as an input field so GEPA
optimizes the *behavioral rules* in the instructions while the evidence stays
in the data path. Seed instructions are grounded in style statistics measured
from the train split, so even the uncompiled program starts evidence-bound.
"""

from __future__ import annotations

import json
from pathlib import Path

import dspy

from ..models import Trace

PERSONA_BRIEF_CHAR_BUDGET = 24_000

_BRIEF_FILE_ORDER = [
    "README.md",
    "context/context-pack.md",
    "context/brain-model.md",
    "context/idea-engine.md",
    "context/taste-and-voice.md",
    "context/tacit-knowledge.md",
    "context/project-patterns.md",
    "context/technical-playbook.md",
    "context/safety-boundaries.md",
    "data/heuristics.json",
]


def persona_brief(persona_dir: Path, budget: int = PERSONA_BRIEF_CHAR_BUDGET) -> str:
    """Bounded concatenation of the package's context files (README load order)."""
    parts: list[str] = []
    used = 0
    for rel in _BRIEF_FILE_ORDER:
        path = persona_dir / rel
        if not path.is_file():
            continue
        text = path.read_text()
        if rel.endswith(".json"):
            try:
                text = json.dumps(json.loads(text), indent=2)
            except ValueError:
                pass
        block = f"\n\n===== {rel} =====\n{text}"
        if used + len(block) > budget:
            block = block[: budget - used]
        parts.append(block)
        used += len(block)
        if used >= budget:
            break
    return "".join(parts).strip()


def _style_stats(train_traces: list[Trace]) -> dict:
    behaviors = [t.behavior.content for t in train_traces if t.behavior.content]
    if not behaviors:
        return {}
    lengths = sorted(len(b) for b in behaviors)
    lowercase_starts = sum(1 for b in behaviors if b[:1].islower())
    return {
        "n": len(behaviors),
        "median_len": lengths[len(lengths) // 2],
        "p90_len": lengths[min(len(lengths) - 1, int(len(lengths) * 0.9))],
        "lowercase_start_ratio": round(lowercase_starts / len(behaviors), 2),
    }


def seed_instructions(train_traces: list[Trace]) -> tuple[str, str]:
    """Seed (draft, refine) instructions grounded in measured train-split style."""
    stats = _style_stats(train_traces)
    style = ""
    if stats:
        style = (
            f" Measured from {stats['n']} real samples: median length "
            f"{stats['median_len']} chars, 90th percentile {stats['p90_len']} chars, "
            f"{int(stats['lowercase_start_ratio'] * 100)}% start lowercase. "
            "Stay inside these bounds."
        )
    draft = (
        "You are producing the exact artifact a specific person would write. "
        "The persona_brief describes their voice, taste, projects, and heuristics; "
        "treat it as evidence, not as content to recite. Write the artifact for the "
        "task and context as this person would: their length, formatting, diction, "
        "and judgment. Output only the artifact text — no meta-commentary." + style
    )
    refine = (
        "You are the person's taste filter. Rewrite the draft so it would pass a "
        "forensic authorship test against the person's real writing: cut generic "
        "phrasing, match their typical length and casing, keep their specificity "
        "and opinions. If the draft already passes, return it unchanged. Output "
        "only the final artifact text." + style
    )
    return draft, refine


class DraftBehavior(dspy.Signature):
    """Write the artifact this person would produce for the task and context."""

    persona_brief: str = dspy.InputField(desc="evidence-bound persona package excerpts")
    task: str = dspy.InputField(desc="what artifact to produce")
    context: str = dspy.InputField(desc="the situation the artifact responds to")
    draft: str = dspy.OutputField(desc="the artifact text, nothing else")


class RefineBehavior(dspy.Signature):
    """Rewrite the draft so it is indistinguishable from the person's real writing."""

    persona_brief: str = dspy.InputField(desc="evidence-bound persona package excerpts")
    task: str = dspy.InputField(desc="what artifact to produce")
    context: str = dspy.InputField(desc="the situation the artifact responds to")
    draft: str = dspy.InputField(desc="candidate artifact to refine")
    output: str = dspy.OutputField(desc="the final artifact text, nothing else")


class PersonaProgram(dspy.Module):
    """draft -> refine persona program; persona_brief is bound at construction."""

    def __init__(
        self,
        brief: str,
        draft_instructions: str | None = None,
        refine_instructions: str | None = None,
    ):
        super().__init__()
        self.brief = brief
        draft_sig = DraftBehavior
        refine_sig = RefineBehavior
        if draft_instructions:
            draft_sig = DraftBehavior.with_instructions(draft_instructions)
        if refine_instructions:
            refine_sig = RefineBehavior.with_instructions(refine_instructions)
        self.draft = dspy.Predict(draft_sig)
        self.refine = dspy.Predict(refine_sig)

    def forward(self, task: str, context: str) -> dspy.Prediction:
        drafted = self.draft(persona_brief=self.brief, task=task, context=context)
        refined = self.refine(
            persona_brief=self.brief, task=task, context=context, draft=drafted.draft
        )
        return dspy.Prediction(output=refined.output)
