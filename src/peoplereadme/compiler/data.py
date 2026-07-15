"""Traces -> dspy.Example datasets with strict split isolation (PRD 9.2, 10).

Train examples feed the optimizer; dev examples are its validation set. Test
traces are refused here entirely — the harness owns them.
"""

from __future__ import annotations

import dspy

from ..harness.pairwise import MIN_PAIRWISE_QUALITY
from ..models import Trace

_TASKS = {
    "post": "Write the post this person would publish right now.",
    "thread": "Write the next post this person would add to the thread below.",
    "reply": "Write the reply this person would post.",
    "commit": "Write the commit message this person would write for this change.",
    "pr_review": "Write the code review comment this person would leave.",
    "launch": "Write the launch post this person would publish for this artifact.",
    "article": "Write the article or blog post this person would publish.",
    "decision": "State the decision this person would make and their rationale.",
}


def trace_task(trace: Trace) -> str:
    return _TASKS.get(trace.kind, "Write the output this person would produce.")


def trace_to_example(trace: Trace) -> dspy.Example:
    return dspy.Example(
        task=trace_task(trace),
        context=trace.context.content or "(no context; standalone artifact)",
        output=trace.behavior.content,
        trace_id=trace.id,
        kind=trace.kind,
        weight=trace.context.reconstruction_quality,
    ).with_inputs("task", "context")


def build_datasets(
    traces: list[Trace],
    min_quality: float = MIN_PAIRWISE_QUALITY,
    max_train: int | None = None,
    max_dev: int | None = None,
) -> tuple[list[dspy.Example], list[dspy.Example]]:
    """(train, dev) examples; test/live traces never leave this function."""

    def pick(split: str, cap: int | None) -> list[dspy.Example]:
        pool = [
            t
            for t in traces
            if t.split == split and t.context.reconstruction_quality >= min_quality
        ]
        pool.sort(key=lambda t: t.context.reconstruction_quality, reverse=True)
        if cap is not None:
            pool = pool[:cap]
        return [trace_to_example(t) for t in pool]

    return pick("train", max_train), pick("dev", max_dev)

