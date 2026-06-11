"""Trace extraction, split assignment, and compilability tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from peoplereadme.evidence import EvidenceItem, append_evidence
from peoplereadme.traces import (
    assign_splits,
    compilability_score,
    extract_traces,
    write_traces,
)


def _ts(i: int) -> str:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    return (base + timedelta(hours=i)).isoformat()


def seed_evidence(persona_dir: Path, n_posts: int = 20) -> None:
    x_items = []
    for i in range(n_posts):
        x_items.append(
            EvidenceItem(
                source="x-archive",
                url=f"https://x.com/u/status/{i}",
                timestamp=_ts(i),
                content=f"post {i}",
                kind="post",
                extra={"tweet_id": str(i)},
            )
        )
    # A self-thread continuation of tweet 0 and a reply to someone else.
    x_items.append(
        EvidenceItem(
            source="x-archive",
            url="https://x.com/u/status/100",
            timestamp=_ts(n_posts),
            content="thread part 2",
            kind="reply",
            extra={"tweet_id": "100", "in_reply_to_status_id": "0"},
        )
    )
    x_items.append(
        EvidenceItem(
            source="x-archive",
            url="https://x.com/u/status/101",
            timestamp=_ts(n_posts + 1),
            content="@other agreed",
            kind="reply",
            extra={"tweet_id": "101", "in_reply_to_status_id": "999"},
        )
    )
    append_evidence(persona_dir, "x-archive", x_items)
    append_evidence(
        persona_dir,
        "github",
        [
            EvidenceItem(
                source="github",
                url="https://github.com/u/r/commit/abc",
                timestamp=_ts(n_posts + 2),
                content="fix parser",
                kind="commit",
                extra={"repo": "u/r"},
            )
        ],
    )
    append_evidence(
        persona_dir,
        "rss",
        [
            EvidenceItem(
                source="rss",
                url="https://blog.example/one",
                timestamp=_ts(n_posts + 3),
                content="Post one",
                kind="article",
            )
        ],
    )


def test_extract_traces_kinds_and_quality(tmp_path: Path):
    persona_dir = tmp_path / "personas" / "p"
    seed_evidence(persona_dir)
    traces = extract_traces(persona_dir, "p")
    by_kind = {t.kind: t for t in traces}
    assert set(by_kind) == {"post", "thread", "reply", "commit", "article"}
    thread = by_kind["thread"]
    assert thread.context.content == "post 0"
    assert thread.context.reconstruction_quality == 0.8
    assert by_kind["reply"].context.reconstruction_quality == 0.1
    assert by_kind["post"].context.type == "prompt_free"
    assert by_kind["commit"].context.type == "prior_state"
    assert all(t.source.hash.startswith("sha256:") for t in traces)


def test_splits_chronological(tmp_path: Path):
    persona_dir = tmp_path / "personas" / "p"
    seed_evidence(persona_dir, n_posts=96)  # 100 traces total
    traces = assign_splits(extract_traces(persona_dir, "p"))
    assert len(traces) == 100
    assert [t.split for t in traces[:70]] == ["train"] * 70
    assert [t.split for t in traces[70:85]] == ["dev"] * 15
    assert [t.split for t in traces[85:]] == ["test"] * 15
    # Test split is the newest slice.
    assert max(t.timestamp for t in traces[:70]) < min(t.timestamp for t in traces[85:])


def test_single_trace_goes_to_train(tmp_path: Path):
    persona_dir = tmp_path / "personas" / "p"
    append_evidence(
        persona_dir,
        "rss",
        [
            EvidenceItem(
                source="rss",
                url="https://blog.example/one",
                timestamp=_ts(0),
                content="Post one",
                kind="article",
            )
        ],
    )
    traces = assign_splits(extract_traces(persona_dir, "p"))
    assert [t.split for t in traces] == ["train"]


def test_compilability_tolerates_bad_timestamps(tmp_path: Path):
    persona_dir = tmp_path / "personas" / "p"
    append_evidence(
        persona_dir,
        "rss",
        [
            EvidenceItem(
                source="rss",
                url="https://blog.example/bad",
                timestamp="not-a-date",
                content="No pubDate",
                kind="article",
            )
        ],
    )
    traces = assign_splits(extract_traces(persona_dir, "p"))
    result = compilability_score(traces)
    assert result.score >= 0


def test_compilability_bands(tmp_path: Path):
    assert compilability_score([]).band == "not_compilable"
    persona_dir = tmp_path / "personas" / "p"
    seed_evidence(persona_dir, n_posts=96)
    traces = assign_splits(extract_traces(persona_dir, "p"))
    result = compilability_score(traces)
    assert 0 < result.score <= 100
    assert result.band in ("not_compilable", "partial", "full")


def test_write_traces_outputs(tmp_path: Path):
    persona_dir = tmp_path / "personas" / "p"
    seed_evidence(persona_dir)
    traces = assign_splits(extract_traces(persona_dir, "p"))
    write_traces(persona_dir, traces, compilability_score(traces))
    lines = (persona_dir / "traces" / "traces.jsonl").read_text().splitlines()
    assert len(lines) == len(traces)
    splits = json.loads((persona_dir / "traces" / "splits.json").read_text())
    assert splits["counts"]["train"] + splits["counts"]["dev"] + splits["counts"]["test"] == len(
        traces
    )
    assert "compilability" in splits
    assert set(splits["splits"].values()) <= {"train", "dev", "test"}
