"""Harness tests: stats, pairwise judging, dimensions, calibration, rubric, run."""

from __future__ import annotations

import json
import sys
import types
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from peoplereadme.harness.calibration import export_calibration, import_calibration
from peoplereadme.harness.dimensions import score_dimensions
from peoplereadme.harness.generation import behavior_prompt, package_as_prompt
from peoplereadme.harness.lm import CachedLM, extract_json
from peoplereadme.harness.pairwise import (
    eligible_pairwise_traces,
    judge_pair,
    run_pairwise,
)
from peoplereadme.harness.rubric import load_rubric, write_default_rubric
from peoplereadme.harness.run import run_eval
from peoplereadme.harness.stats import bootstrap_ci, cohens_kappa, weighted_mean
from peoplereadme.models import Trace, TraceBehavior, TraceContext, TraceSource


def make_trace(i: int, quality: float = 0.8, split: str = "test", kind: str = "post") -> Trace:
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


class ScriptedLM:
    """Deterministic fake LM: responds via a callable(system, user) -> str."""

    def __init__(self, fn, model: str = "fake-model"):
        self.fn = fn
        self.model = model
        self.calls = 0

    def complete(self, system: str, user: str) -> str:
        self.calls += 1
        return self.fn(system, user)


def perfect_judge(system: str, user: str) -> str:
    """Always identifies the real text (contains 'real behavior')."""
    a = user.split("Candidate A:\n", 1)[1].split("\n\nCandidate B:", 1)[0]
    pick = "A" if "real behavior" in a else "B"
    return json.dumps({"real": pick, "confidence": 0.9, "reason": "test"})


def fooled_judge(system: str, user: str) -> str:
    """Always picks the generated text (never the real one)."""
    a = user.split("Candidate A:\n", 1)[1].split("\n\nCandidate B:", 1)[0]
    pick = "B" if "real behavior" in a else "A"
    return json.dumps({"real": pick, "confidence": 0.6})


def positional_judge(system: str, user: str) -> str:
    """Always picks A regardless of content (pure position bias)."""
    return json.dumps({"real": "A", "confidence": 0.5})


def test_weighted_mean_and_bootstrap():
    assert weighted_mean([1.0, 0.0], [1.0, 1.0]) == 0.5
    assert weighted_mean([1.0, 0.0], [1.0, 0.0]) == 1.0
    lo, hi = bootstrap_ci(
        [1.0] * 50 + [0.0] * 50,
        [1.0] * 100,
        lambda v, w: weighted_mean(v, w),
        seed=1,
    )
    assert 0.3 < lo < 0.5 < hi < 0.7


def test_cohens_kappa():
    assert cohens_kappa(["A", "B"] * 10, ["A", "B"] * 10) == 1.0
    # Independent raters -> kappa near 0.
    assert abs(cohens_kappa(["A", "A", "B", "B"], ["A", "B", "A", "B"])) < 1e-9


def test_extract_json_variants():
    assert extract_json('{"real": "A"}') == {"real": "A"}
    assert extract_json('```json\n{"real": "B", "x": {"y": 1}}\n```')["real"] == "B"
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_judge_pair_position_swap():
    trace = make_trace(1)
    perfect = ScriptedLM(perfect_judge)
    result = judge_pair(perfect, trace, "generated text")
    assert result.correct == 1.0
    assert perfect.calls == 2  # both orders judged

    fooled = ScriptedLM(fooled_judge)
    assert judge_pair(fooled, trace, "generated text").correct == 0.0

    positional = ScriptedLM(positional_judge)
    assert judge_pair(positional, trace, "generated text").correct == 0.5


def test_run_pairwise_scores_and_bias():
    traces = [make_trace(i) for i in range(20)]
    gens = {t.id: f"generated {t.id}" for t in traces}
    perfect = run_pairwise(ScriptedLM(perfect_judge), traces, gens)
    assert perfect.judge_accuracy == 1.0
    assert perfect.score == 0.0  # fully distinguishable
    fooled = run_pairwise(ScriptedLM(fooled_judge), traces, gens)
    assert fooled.judge_accuracy == 0.0
    assert fooled.score == 1.0  # clamped
    positional = run_pairwise(ScriptedLM(positional_judge), traces, gens)
    assert positional.judge_accuracy == 0.5
    assert positional.score == 1.0
    assert positional.position_bias == 1.0  # picks A in both orders


def test_eligible_pairwise_excludes_low_quality():
    traces = [make_trace(0, quality=0.1), make_trace(1, quality=0.2), make_trace(2, split="train")]
    eligible = eligible_pairwise_traces(traces)
    assert [t.id for t in eligible] == ["trace_000001"]


def test_rubric_write_and_load(tmp_path: Path):
    path = write_default_rubric(tmp_path)
    rubric = load_rubric(tmp_path)
    assert path.is_file()
    assert rubric.version == 1
    ids = {d.id for d in rubric.dimensions}
    assert ids == {
        "evidence_fidelity",
        "voice_fit",
        "taste_fit",
        "scope_discipline",
        "data_seam_quality",
        "anti_generic",
    }


def test_score_dimensions(tmp_path: Path):
    rubric = load_rubric(tmp_path)
    traces = [make_trace(i) for i in range(3)]
    gens = {t.id: "gen" for t in traces}

    def dim_judge(system: str, user: str) -> str:
        return json.dumps({"scores": {d.id: 4 for d in rubric.dimensions}})

    scores = score_dimensions(ScriptedLM(dim_judge), rubric, traces, gens)
    assert all(v == 4.0 for v in scores.values())


def test_package_as_prompt_and_behavior_prompt(tmp_path: Path):
    (tmp_path / "context").mkdir(parents=True)
    (tmp_path / "README.md").write_text("# Persona readme")
    (tmp_path / "context" / "context-pack.md").write_text("pack content")
    prompt = package_as_prompt(tmp_path)
    assert "Persona readme" in prompt
    assert "pack content" in prompt
    bp = behavior_prompt(make_trace(1, kind="thread"))
    assert "thread" in bp.lower()
    assert "context 1" in bp


def test_calibration_roundtrip(tmp_path: Path):
    traces = [make_trace(i) for i in range(60)]
    gens = {t.id: f"generated {t.id}" for t in traces}
    pw = run_pairwise(ScriptedLM(perfect_judge), traces, gens)
    blind, key = export_calibration(tmp_path, "batch1", traces, gens, pw.pairs, seed=1)
    assert blind.is_file() and key.is_file()
    rows = [json.loads(line) for line in blind.read_text().splitlines()]
    assert len(rows) == 60
    assert all(row["human_pick"] is None for row in rows)

    # Human agrees with the (perfect) judge on every pair -> kappa 1, valid.
    answers = json.loads(key.read_text())
    for row in rows:
        row["human_pick"] = answers[row["pair_id"]]["judge_pick"]
    ratings = tmp_path / "ratings.jsonl"
    ratings.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    result = import_calibration(tmp_path, "batch1", ratings)
    assert result.kappa == 1.0
    assert result.valid
    assert result.human_accuracy == 1.0

    # Human picks the opposite of the real answer everywhere -> kappa -1, invalid.
    for row in rows:
        row["human_pick"] = "B" if answers[row["pair_id"]]["real"] == "A" else "A"
    ratings.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    result = import_calibration(tmp_path, "batch1", ratings)
    assert result.kappa <= -0.9
    assert not result.valid


def test_cached_lm(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("PEOPLEREADME_CACHE", str(tmp_path))
    inner = ScriptedLM(lambda s, u: "output-1")
    cached = CachedLM(inner)
    assert cached.complete("sys", "user") == "output-1"
    assert cached.complete("sys", "user") == "output-1"
    assert inner.calls == 1


def test_eval_cli_end_to_end(tmp_repo: Path, monkeypatch, tmp_path: Path):
    from typer.testing import CliRunner

    import peoplereadme.harness.lm as lm_mod
    from peoplereadme.cli import app

    def gen_or_judge(system: str, user: str) -> str:
        if "forensic evaluator" in system:
            return perfect_judge(system, user)
        if "scoring an AI-generated artifact" in system:
            return json.dumps({"scores": {"voice_fit": 4}})
        return "generated artifact"

    monkeypatch.setattr(
        lm_mod, "build_lm", lambda model, **kw: ScriptedLM(gen_or_judge, model=model)
    )
    monkeypatch.chdir(tmp_repo)
    runner = CliRunner()
    assert runner.invoke(app, ["init", "test-person", "--class", "self"]).exit_code == 0
    persona_dir = tmp_repo / "personas" / "test-person"
    traces = [make_trace(i, split="test") for i in range(6)]
    (persona_dir / "traces").mkdir(exist_ok=True)
    (persona_dir / "traces" / "traces.jsonl").write_text(
        "\n".join(t.model_dump_json() for t in traces) + "\n"
    )
    result = runner.invoke(app, ["eval", "test-person", "--model", "fake/model"])
    assert result.exit_code == 0, result.output
    assert "indistinguishability:" in result.output
    assert "voice_fit" in result.output
    assert "WARNING: n_pairs < 100" in result.output
    assert (persona_dir / "evals" / "rubrics" / "v1.json").is_file()

    # Calibration flow: rate the exported batch in agreement with the judge.
    cal_dir = persona_dir / "evals" / "fidelity" / "calibration"
    blind = next(cal_dir.glob("*.jsonl"))
    batch = blind.name[: -len(".jsonl")]
    answers = json.loads((cal_dir / f"{batch}.answers.json").read_text())
    rows = [json.loads(line) for line in blind.read_text().splitlines()]
    for row in rows:
        row["human_pick"] = answers[row["pair_id"]]["judge_pick"]
    ratings = tmp_path / "ratings.jsonl"
    ratings.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    result = runner.invoke(
        app,
        ["calibrate", "test-person", "--batch", batch, "--ratings", str(ratings)],
    )
    assert "kappa: 1.0" in result.output
    # Fewer than 50 rated pairs -> invalid card, exit 1.
    assert result.exit_code == 1
    stamped = json.loads((persona_dir / "evals" / "fidelity" / f"{batch}.json").read_text())
    assert stamped["judge"]["human_agreement_kappa"] == 1.0


def test_eval_cli_clean_error_on_lm_failure(tmp_repo: Path, monkeypatch):
    from typer.testing import CliRunner

    import peoplereadme.harness.lm as lm_mod
    from peoplereadme.cli import app
    from peoplereadme.harness.lm import LMError

    def failing(system: str, user: str) -> str:
        raise LMError("model call failed (openai/x): Incorrect API key provided")

    monkeypatch.setattr(lm_mod, "build_lm", lambda model, **kw: ScriptedLM(failing, model=model))
    monkeypatch.chdir(tmp_repo)
    runner = CliRunner()
    runner.invoke(app, ["init", "p", "--class", "self"])
    persona_dir = tmp_repo / "personas" / "p"
    (persona_dir / "traces").mkdir(exist_ok=True)
    (persona_dir / "traces" / "traces.jsonl").write_text(
        make_trace(1, split="test").model_dump_json() + "\n"
    )
    result = runner.invoke(app, ["eval", "p", "--model", "openai/x"])
    assert result.exit_code == 1
    assert "Error running eval: model call failed" in result.output
    assert "Traceback" not in result.output


def test_litellm_retries_without_temperature(monkeypatch):
    from peoplereadme.harness.lm import LiteLLM

    class FakeBadRequest(Exception):
        pass

    calls: list[dict] = []

    def fake_completion(**kwargs):
        calls.append(kwargs)
        if "temperature" in kwargs:
            raise FakeBadRequest("Unsupported value: 'temperature' does not support 0.7")

        class _Msg:
            content = "ok"

        class _Choice:
            message = _Msg()

        class _Resp:
            choices = [_Choice()]

        return _Resp()

    fake_litellm = types.SimpleNamespace(
        completion=fake_completion, BadRequestError=FakeBadRequest
    )
    monkeypatch.setitem(sys.modules, "litellm", fake_litellm)
    out = LiteLLM("openai/gpt-5.5", temperature=0.7).complete("sys", "usr")
    assert out == "ok"
    assert len(calls) == 2  # first with temperature (fails), retry without
    assert "temperature" not in calls[1]


def test_litellm_other_bad_request_not_retried(monkeypatch):
    from peoplereadme.harness.lm import LiteLLM, LMError

    class FakeBadRequest(Exception):
        pass

    def fake_completion(**kwargs):
        raise FakeBadRequest("some unrelated 400")

    fake_litellm = types.SimpleNamespace(
        completion=fake_completion, BadRequestError=FakeBadRequest
    )
    monkeypatch.setitem(sys.modules, "litellm", fake_litellm)
    with pytest.raises(LMError):
        LiteLLM("openai/gpt-4o-mini", temperature=0.7).complete("sys", "usr")


def test_run_eval_end_to_end(tmp_path: Path):
    persona_dir = tmp_path / "personas" / "p"
    (persona_dir / "traces").mkdir(parents=True)
    (persona_dir / "context").mkdir(parents=True)
    (persona_dir / "README.md").write_text("# p persona")
    traces = [make_trace(i, split="test") for i in range(12)]
    traces += [make_trace(100 + i, split="train") for i in range(5)]
    (persona_dir / "traces" / "traces.jsonl").write_text(
        "\n".join(t.model_dump_json() for t in traces) + "\n"
    )

    def gen_or_judge(system: str, user: str) -> str:
        if "forensic evaluator" in system:
            return perfect_judge(system, user)
        if "scoring an AI-generated artifact" in system:
            return json.dumps({"scores": {"voice_fit": 3}})
        return "generated artifact"

    lm = ScriptedLM(gen_or_judge)
    report, path = run_eval(persona_dir, "p", lm, lm, n_pairs=10, seed=0)
    assert path.is_file()
    assert report.n_test == 10
    assert report.indistinguishability.judge_accuracy == 1.0
    assert report.indistinguishability.score == 0.0
    assert report.baseline_delta["vs_raw_model"] == "+0.00"
    assert report.dimensions["voice_fit"] == 3.0
    assert (persona_dir / "evals" / "fidelity" / "latest.json").is_file()
    batch_files = list((persona_dir / "evals" / "fidelity" / "calibration").glob("*.jsonl"))
    assert len(batch_files) == 1
    data = json.loads(path.read_text())
    assert data["judge"]["human_agreement_kappa"] is None
