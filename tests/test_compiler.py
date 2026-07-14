"""Compiler tests: datasets, program, metric, compile/save/load, harness bridge."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import dspy
import pytest
from dspy.utils.dummies import DummyLM

from peoplereadme.compiler import (
    build_datasets,
    generate_compiled,
    load_compiled,
    make_feedback_metric,
    persona_brief,
    run_compile,
    seed_instructions,
    trace_to_example,
)
from peoplereadme.compiler.program import PersonaProgram
from peoplereadme.models import Trace, TraceBehavior, TraceContext, TraceSource


def make_trace(i: int, quality: float = 0.8, split: str = "train", kind: str = "post") -> Trace:
    ts = (datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=i)).isoformat()
    ctx_type = "thread" if kind in ("thread", "reply") else "prompt_free"
    return Trace(
        id=f"trace_{i:06d}",
        persona_id="p",
        kind=kind,
        context=TraceContext(type=ctx_type, content=f"context {i}", reconstruction_quality=quality),
        behavior=TraceBehavior(content=f"real behavior {i}", artifact_url=None),
        source=TraceSource(url=f"https://x.com/u/status/{i}", tier="first_party", hash="sha256:x"),
        timestamp=ts,
        split=split,
    )


class FakeJudge:
    model = "fake-judge"

    def __init__(self, response: str):
        self.response = response
        self.calls = 0

    def complete(self, system: str, user: str) -> str:
        self.calls += 1
        return self.response


def write_traces_file(persona_dir, traces):
    tdir = persona_dir / "traces"
    tdir.mkdir(parents=True, exist_ok=True)
    (tdir / "traces.jsonl").write_text(
        "".join(t.model_dump_json() + "\n" for t in traces)
    )


def test_trace_to_example_fields():
    ex = trace_to_example(make_trace(1, kind="reply"))
    assert ex.task == "Write the reply this person would post."
    assert ex.context == "context 1"
    assert ex.output == "real behavior 1"
    assert set(ex.inputs().keys()) == {"task", "context"}


def test_build_datasets_split_isolation_and_quality_filter():
    traces = (
        [make_trace(i, split="train") for i in range(5)]
        + [make_trace(10, split="train", quality=0.1)]
        + [make_trace(20, split="dev"), make_trace(21, split="dev")]
        + [make_trace(30, split="test"), make_trace(31, split="live")]
    )
    train, dev = build_datasets(traces)
    train_ids = {e.trace_id for e in train}
    dev_ids = {e.trace_id for e in dev}
    assert len(train) == 5 and "trace_000010" not in train_ids
    assert dev_ids == {"trace_000020", "trace_000021"}
    assert not (train_ids | dev_ids) & {"trace_000030", "trace_000031"}


def test_build_datasets_caps_prefer_high_quality():
    traces = [make_trace(i, quality=0.3 + i * 0.1) for i in range(5)]
    train, _ = build_datasets(traces, max_train=2)
    assert [e.trace_id for e in train] == ["trace_000004", "trace_000003"]


def test_persona_brief_bounded(tmp_path):
    (tmp_path / "README.md").write_text("brief content " * 10)
    ctx = tmp_path / "context"
    ctx.mkdir()
    (ctx / "taste-and-voice.md").write_text("x" * 100_000)
    brief = persona_brief(tmp_path, budget=500)
    assert "brief content" in brief
    assert len(brief) <= 500


def test_seed_instructions_include_style_stats():
    draft, refine = seed_instructions([make_trace(i) for i in range(4)])
    assert "median length" in draft and "median length" in refine
    assert "Output only the artifact" in draft


def test_seed_instructions_no_traces():
    draft, refine = seed_instructions([])
    assert "median length" not in draft
    assert "taste filter" in refine


def test_feedback_metric_score_and_feedback():
    judge = FakeJudge('{"score": 0.7, "feedback": "too long; cut filler."}')
    metric = make_feedback_metric(judge)
    gold = trace_to_example(make_trace(1))
    result = metric(gold, dspy.Prediction(output="a punchy post"))
    assert result.score == 0.7
    assert "too long" in result.feedback


def test_feedback_metric_handles_empty_and_malformed():
    metric = make_feedback_metric(FakeJudge("not json at all"))
    gold = trace_to_example(make_trace(1))
    assert metric(gold, dspy.Prediction(output="")).score == 0.0
    bad = metric(gold, dspy.Prediction(output="something"))
    assert bad.score == 0.0 and "unparseable" in bad.feedback


def test_feedback_metric_flags_length_drift():
    judge = FakeJudge('{"score": 0.4, "feedback": "generic."}')
    metric = make_feedback_metric(judge)
    gold = trace_to_example(make_trace(1))
    result = metric(gold, dspy.Prediction(output="x" * 200))
    assert "Length drift" in result.feedback


def _dummy_lm(n: int = 200):
    return DummyLM([{"draft": f"draft {i}", "output": f"output {i}"} for i in range(n)])


def test_persona_program_runs_with_dummy_lm():
    with dspy.context(lm=_dummy_lm()):
        program = PersonaProgram("brief", "draft rules", "refine rules")
        result = program(task="Write the post.", context="ctx")
    assert result.output.startswith("output")
    assert program.draft.signature.instructions == "draft rules"


def test_run_compile_none_saves_and_loads(tmp_path):
    (tmp_path / "README.md").write_text("persona brief")
    traces = [make_trace(i, split="train") for i in range(5)] + [
        make_trace(10, split="dev"),
        make_trace(30, split="test"),
    ]
    write_traces_file(tmp_path, traces)
    judge = FakeJudge('{"score": 0.5, "feedback": "ok"}')
    with dspy.context(lm=_dummy_lm()):
        result = run_compile(
            tmp_path, "p", judge, task_model="dummy", optimizer="none"
        )
        assert result.n_train == 5 and result.n_dev == 1
        assert result.seed_dev_score == result.compiled_dev_score == 0.5
        assert result.dataset_hash.startswith("sha256:")
        assert (tmp_path / "compiled" / "program.json").is_file()
        lock = json.loads((tmp_path / "compiled" / "compile.lock.json").read_text())
        assert lock["optimizer"] == "none"
        assert lock["reflection_model"] is None
        program, loaded_lock = load_compiled(tmp_path)
        assert loaded_lock["persona"] == "p"
        assert "median length" in program.draft.signature.instructions
        gen = generate_compiled(program, [make_trace(30, split="test")])
    assert set(gen) == {"trace_000030"}
    assert gen["trace_000030"].startswith("output")


def test_run_compile_requires_min_train(tmp_path):
    write_traces_file(tmp_path, [make_trace(0, split="train")])
    with pytest.raises(ValueError, match="train examples"):
        run_compile(tmp_path, "p", FakeJudge("{}"), task_model="dummy", optimizer="none")


def test_run_compile_gepa_requires_reflection_and_dev(tmp_path):
    write_traces_file(tmp_path, [make_trace(i, split="train") for i in range(5)])
    judge = FakeJudge('{"score": 0.5, "feedback": "ok"}')
    with pytest.raises(ValueError, match="dev split"):
        run_compile(tmp_path, "p", judge, task_model="dummy", optimizer="gepa")
    write_traces_file(
        tmp_path,
        [make_trace(i, split="train") for i in range(5)] + [make_trace(10, split="dev")],
    )
    with dspy.context(lm=_dummy_lm()):
        with pytest.raises(ValueError, match="reflection-model"):
            run_compile(
                tmp_path,
                "p",
                judge,
                task_model="dummy",
                optimizer="gepa",
                reflection_model=None,
                skip_dev_scores=True,
            )


def test_run_compile_unknown_optimizer(tmp_path):
    write_traces_file(
        tmp_path,
        [make_trace(i, split="train") for i in range(5)] + [make_trace(10, split="dev")],
    )
    judge = FakeJudge('{"score": 0.5, "feedback": "ok"}')
    with pytest.raises(ValueError, match="unknown optimizer"):
        run_compile(
            tmp_path, "p", judge, task_model="dummy", optimizer="wat", skip_dev_scores=True
        )


def test_load_compiled_missing(tmp_path):
    with pytest.raises(FileNotFoundError, match="compile"):
        load_compiled(tmp_path)


def test_compile_cli_clean_error_without_traces(tmp_repo, monkeypatch):
    from typer.testing import CliRunner

    from peoplereadme.cli import app

    monkeypatch.chdir(tmp_repo)
    runner = CliRunner()
    runner.invoke(app, ["init", "p", "--class", "self"])
    result = runner.invoke(app, ["compile", "p", "--optimizer", "none"])
    assert result.exit_code == 1
    assert "traces.jsonl" in result.output
    assert "Traceback" not in result.output


def test_run_compile_bootstrap_with_dummy_lm(tmp_path):
    (tmp_path / "README.md").write_text("persona brief")
    traces = [make_trace(i, split="train") for i in range(5)] + [make_trace(10, split="dev")]
    write_traces_file(tmp_path, traces)
    judge = FakeJudge('{"score": 0.9, "feedback": "great"}')
    with dspy.context(lm=_dummy_lm(400)):
        result = run_compile(
            tmp_path, "p", judge, task_model="dummy", optimizer="bootstrap",
            skip_dev_scores=True,
        )
    assert result.optimizer == "bootstrap"
    assert (tmp_path / "compiled" / "program.json").is_file()
