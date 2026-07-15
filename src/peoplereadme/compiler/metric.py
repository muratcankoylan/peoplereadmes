"""GEPA-ready fidelity metric backed by the M2 harness judge.

Returns dspy.Prediction(score, feedback): the float drives candidate selection
(Pareto frontier), the natural-language feedback drives GEPA's reflection LM.
The judge compares the generated artifact to the real one on the same
authorship dimensions the harness rubric codifies, plus the observed failure
modes (length drift, generic phrasing).
"""

from __future__ import annotations

import dspy

from ..harness.lm import LM, extract_json
from ..harness.stats import clamp

METRIC_SYSTEM = (
    "You are a forensic authorship evaluator. Compare a generated artifact to the "
    "real artifact the person actually wrote for the same task and context. Score "
    "how likely the generated one is to pass as written by the same person: voice, "
    "taste, specificity, judgment, length, formatting, casing. Be harsh; generic "
    "competence scores low. Respond with JSON only: "
    '{"score": <0.0-1.0>, "feedback": "<2-3 sentences: the strongest tells that '
    'give the generated artifact away, and what to change>"}'
)


def _metric_prompt(gold: dspy.Example, output: str) -> str:
    return (
        f"Task: {gold.task}\n\nContext:\n{gold.context}\n\n"
        f"Real artifact by the person:\n{gold.output}\n\n"
        f"Generated artifact:\n{output}\n\nJSON only."
    )


def make_feedback_metric(judge: LM):
    """Metric closure over a harness judge LM (temperature 0, disk-cached)."""

    def metric(
        gold: dspy.Example,
        pred: dspy.Prediction,
        trace=None,
        pred_name=None,
        pred_trace=None,
    ) -> dspy.Prediction:
        output = (pred.output or "").strip()
        if not output:
            return dspy.Prediction(score=0.0, feedback="Empty output; produce the artifact.")
        raw = judge.complete(METRIC_SYSTEM, _metric_prompt(gold, output))
        try:
            data = extract_json(raw)
            score = clamp(float(data.get("score", 0.0)))
            feedback = str(data.get("feedback", "")).strip() or "No feedback returned."
        except (TypeError, ValueError):
            return dspy.Prediction(
                score=0.0, feedback="Judge response unparseable; treat as failure."
            )
        real_len, gen_len = len(gold.output), len(output)
        if real_len and gen_len > 2 * real_len:
            feedback += (
                f" Length drift: generated {gen_len} chars vs real {real_len}; "
                "cut aggressively."
            )
        return dspy.Prediction(score=score, feedback=feedback)

    return metric


def as_float_metric(feedback_metric):
    """Adapter for optimizers that expect a plain float/bool metric."""

    def metric(gold, pred, trace=None):
        result = feedback_metric(gold, pred, trace)
        return result.score if trace is None else result.score >= 0.5

    return metric
