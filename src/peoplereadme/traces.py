"""Trace extraction: evidence -> (context -> behavior) pairs, splits, compilability.

Rules-based (PRD 9.2): replies inline the post they answer when it exists in
evidence; self-threads inline preceding posts; commits get a prior-state context;
standalone posts are prompt_free with low reconstruction quality. Each trace
carries reconstruction_quality in [0, 1]; the harness weights by it.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .evidence import EvidenceItem, load_evidence
from .models import Compilability, Trace, TraceBehavior, TraceContext, TraceSource

SPLIT_FRACTIONS = {"train": 0.70, "dev": 0.15}  # remainder -> test
RECENCY_WINDOW_DAYS = 180
TRACE_KIND_TARGET = 8  # distinct kinds in the trace schema


def _source(item: EvidenceItem) -> TraceSource:
    return TraceSource(url=item.url, tier=item.tier, hash=item.hash)


def _by_tweet_id(items: list[EvidenceItem]) -> dict[str, EvidenceItem]:
    return {
        item.extra["tweet_id"]: item
        for item in items
        if item.extra.get("tweet_id")
    }


def _thread_context(item: EvidenceItem, by_id: dict[str, EvidenceItem]) -> list[str]:
    """Walk the in_reply_to chain backwards collecting preceding posts."""
    chain: list[str] = []
    current = item
    while True:
        parent_id = current.extra.get("in_reply_to_status_id")
        parent = by_id.get(parent_id) if parent_id else None
        if parent is None or len(chain) >= 10:
            return list(reversed(chain))
        chain.append(parent.content)
        current = parent


def _x_trace(item: EvidenceItem, by_id: dict[str, EvidenceItem], persona_id: str, n: int) -> Trace:
    parent_id = item.extra.get("in_reply_to_status_id")
    parent = by_id.get(parent_id) if parent_id else None
    if parent is not None:
        # Parent is in the archive, i.e. the author's own tweet: a self-thread.
        context = TraceContext(
            type="thread",
            content="\n---\n".join(_thread_context(item, by_id)),
            reconstruction_quality=0.8,
        )
        kind = "thread"
    elif parent_id:
        # Reply to someone else's tweet; v1 cannot fetch it (no API dependency).
        kind = "reply"
        context = TraceContext(type="thread", content="", reconstruction_quality=0.1)
    else:
        kind = "post"
        context = TraceContext(type="prompt_free", content="", reconstruction_quality=0.2)
    return Trace(
        id=f"trace_{n:06d}",
        persona_id=persona_id,
        kind=kind,
        context=context,
        behavior=TraceBehavior(content=item.content, artifact_url=item.url),
        source=_source(item),
        timestamp=item.timestamp,
        split="train",
    )


def _commit_trace(item: EvidenceItem, persona_id: str, n: int) -> Trace:
    repo = item.extra.get("repo", "")
    return Trace(
        id=f"trace_{n:06d}",
        persona_id=persona_id,
        kind="commit",
        context=TraceContext(
            type="prior_state",
            content=f"Repository: {repo}",
            reconstruction_quality=0.4,
        ),
        behavior=TraceBehavior(content=item.content, artifact_url=item.url),
        source=_source(item),
        timestamp=item.timestamp,
        split="train",
    )


def _article_trace(item: EvidenceItem, persona_id: str, n: int) -> Trace:
    return Trace(
        id=f"trace_{n:06d}",
        persona_id=persona_id,
        kind="article",
        context=TraceContext(type="prompt_free", content="", reconstruction_quality=0.3),
        behavior=TraceBehavior(content=item.content, artifact_url=item.url),
        source=_source(item),
        timestamp=item.timestamp,
        split="train",
    )


def extract_traces(persona_dir: Path, persona_id: str) -> list[Trace]:
    items = load_evidence(persona_dir)
    by_id = _by_tweet_id(items)
    traces: list[Trace] = []
    for item in sorted(items, key=lambda i: _sort_key(i.timestamp)):
        if item.tier == "press":
            continue
        n = len(traces)
        if item.extra.get("tweet_id") and item.kind in ("post", "reply"):
            traces.append(_x_trace(item, by_id, persona_id, n))
        elif item.kind == "commit":
            traces.append(_commit_trace(item, persona_id, n))
        elif item.kind == "article":
            traces.append(_article_trace(item, persona_id, n))
    return traces


def assign_splits(traces: list[Trace]) -> list[Trace]:
    """Chronological: oldest 70% train, next 15% dev, newest 15% test."""
    ordered = sorted(traces, key=lambda t: _sort_key(t.timestamp))
    n = len(ordered)
    train_end = max(int(n * SPLIT_FRACTIONS["train"]), min(n, 1))
    dev_end = train_end + int(n * SPLIT_FRACTIONS["dev"])
    for i, trace in enumerate(ordered):
        trace.split = "train" if i < train_end else "dev" if i < dev_end else "test"
    return ordered


_MIN_TS = datetime.min.replace(tzinfo=UTC)


def _parse_ts(value: str) -> datetime | None:
    """Parse an ISO timestamp to a UTC-aware datetime; naive values are assumed UTC."""
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _sort_key(value: str) -> datetime:
    return _parse_ts(value) or _MIN_TS


def compilability_score(traces: list[Trace]) -> Compilability:
    """Volume 40%, mean reconstruction quality 25%, kind diversity 20%, recency 15%."""
    if not traces:
        return Compilability(score=0, band="not_compilable")
    volume = min(len(traces) / 500, 1.0) * 40
    mean_quality = (
        sum(t.context.reconstruction_quality for t in traces) / len(traces)
    ) * 25
    diversity = (len({t.kind for t in traces}) / TRACE_KIND_TARGET) * 20
    timestamps = [ts for t in traces if (ts := _parse_ts(t.timestamp)) is not None]
    if timestamps:
        window_start = max(timestamps) - timedelta(days=RECENCY_WINDOW_DAYS)
        recency = (sum(1 for ts in timestamps if ts >= window_start) / len(traces)) * 15
    else:
        recency = 0.0
    score = round(volume + mean_quality + diversity + recency)
    band = "not_compilable" if score < 30 else "partial" if score <= 60 else "full"
    return Compilability(score=score, band=band)


def write_traces(persona_dir: Path, traces: list[Trace], compilability: Compilability) -> None:
    traces_dir = persona_dir / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)
    with (traces_dir / "traces.jsonl").open("w") as fh:
        for trace in traces:
            fh.write(trace.model_dump_json(exclude_none=True) + "\n")
    counts = {
        split: sum(1 for t in traces if t.split == split)
        for split in ("train", "dev", "test", "live")
    }
    splits = {
        "splits": {t.id: t.split for t in traces},
        "counts": counts,
        "compilability": compilability.model_dump(),
    }
    (traces_dir / "splits.json").write_text(json.dumps(splits, indent=2) + "\n")
