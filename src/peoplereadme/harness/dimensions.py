"""Rubric-dimension judging: 1-5 anchored scores per generated output (PRD 9.5)."""

from __future__ import annotations

from ..models import Trace
from .lm import LM, extract_json, pmap
from .rubric import Rubric

DIMENSION_SYSTEM = (
    "You are scoring an AI-generated artifact that simulates a specific person, "
    "against real samples of that person's work. Score each dimension 1-5 using "
    "the anchors provided. Be harsh: 5 means indistinguishable from the person, "
    "3 is the default for competent-but-generic. Respond with JSON only: "
    '{"scores": {"<dimension_id>": <1-5>, ...}}'
)


def _dimension_prompt(rubric: Rubric, trace: Trace, generated: str) -> str:
    dims = "\n".join(
        f"- {d.id} ({d.name}): {d.description}\n"
        f"  1: {d.anchors.get('1', '')}\n  3: {d.anchors.get('3', '')}\n"
        f"  5: {d.anchors.get('5', '')}"
        for d in rubric.dimensions
    )
    ctx = trace.context.content or "(no context)"
    return (
        f"Dimensions:\n{dims}\n\n"
        f"Artifact kind: {trace.kind}\nContext:\n{ctx}\n\n"
        f"Real sample by the person (reference for voice/taste):\n{trace.behavior.content}\n\n"
        f"Generated artifact to score:\n{generated}\n\nJSON only."
    )


def score_dimensions(
    judge: LM,
    rubric: Rubric,
    traces: list[Trace],
    generations: dict[str, str],
    concurrency: int = 1,
) -> dict[str, float]:
    """Mean 1-5 score per rubric dimension across generated outputs."""
    totals: dict[str, list[float]] = {d.id: [] for d in rubric.dimensions}
    pool = [t for t in traces if t.id in generations]

    def judge_one(trace: Trace) -> dict:
        raw = judge.complete(
            DIMENSION_SYSTEM, _dimension_prompt(rubric, trace, generations[trace.id])
        )
        return extract_json(raw).get("scores", {})

    for scores in pmap(judge_one, pool, max_workers=concurrency):
        for dim in rubric.dimensions:
            value = scores.get(dim.id)
            if isinstance(value, int | float) and 1 <= value <= 5:
                totals[dim.id].append(float(value))
    return {
        dim: round(sum(vals) / len(vals), 2) if vals else 0.0 for dim, vals in totals.items()
    }
