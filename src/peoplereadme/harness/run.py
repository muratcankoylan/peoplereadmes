"""Harness orchestration: generate -> judge -> fidelity.json (PRD 9.5, 8.3).

M2 measures the package-as-prompt ceiling against the raw-model baseline;
compiled personas plug into the same runner in M3 as a third condition.
"""

from __future__ import annotations

import json
import random
from datetime import UTC, datetime
from pathlib import Path

from ..models import FidelityReport, Indistinguishability, JudgeInfo, Trace
from .calibration import export_calibration
from .dimensions import score_dimensions
from .generation import RAW_SYSTEM_PROMPT, behavior_prompt, package_as_prompt
from .lm import LM, cost_tracker, pmap
from .pairwise import PairwiseResult, eligible_pairwise_traces, run_pairwise
from .rubric import load_rubric


def load_traces(persona_dir: Path) -> list[Trace]:
    path = persona_dir / "traces" / "traces.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found (run `peoplereadme trace` first)")
    return [
        Trace.model_validate_json(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def generate_all(
    lm: LM, system_prompt: str, traces: list[Trace], concurrency: int = 1
) -> dict[str, str]:
    outputs = pmap(
        lambda t: lm.complete(system_prompt, behavior_prompt(t)), traces, max_workers=concurrency
    )
    return {t.id: out for t, out in zip(traces, outputs, strict=True)}


def _delta(a: float, b: float) -> str:
    return f"{a - b:+.2f}"


def _indist(result: PairwiseResult) -> Indistinguishability:
    return Indistinguishability(
        judge_accuracy=result.judge_accuracy, score=result.score, ci95=result.ci95
    )


def run_eval(
    persona_dir: Path,
    persona_id: str,
    generator: LM,
    judge: LM,
    n_pairs: int = 100,
    seed: int = 0,
    skip_baseline: bool = False,
    compiled_generate=None,
    concurrency: int = 1,
) -> tuple[FidelityReport, Path]:
    """Run the harness; writes evals/fidelity/{date}.json + a calibration batch.

    When compiled_generate (traces -> {trace_id: text}) is given, the headline
    condition is the compiled persona program (M3) and package-as-prompt joins
    the baselines so the compiled-minus-package delta is always reported.
    """
    cost_tracker.reset()
    rubric = load_rubric(persona_dir)
    traces = load_traces(persona_dir)
    pool = eligible_pairwise_traces(traces, split="test")
    rng = random.Random(seed)
    if len(pool) > n_pairs:
        pool = rng.sample(pool, n_pairs)

    package_prompt = package_as_prompt(persona_dir)
    package_gen = generate_all(generator, package_prompt, pool, concurrency=concurrency)
    package_pw = run_pairwise(judge, pool, package_gen, seed=seed, concurrency=concurrency)

    baselines: dict[str, Indistinguishability] = {}
    baseline_delta: dict[str, str] = {}
    if compiled_generate is not None:
        condition = "compiled"
        headline_gen = compiled_generate(pool)
        headline_pw = run_pairwise(judge, pool, headline_gen, seed=seed, concurrency=concurrency)
        baselines["package"] = _indist(package_pw)
        baseline_delta["vs_package"] = _delta(headline_pw.score, package_pw.score)
    else:
        condition = "package"
        headline_gen = package_gen
        headline_pw = package_pw
    dims = score_dimensions(judge, rubric, pool, headline_gen, concurrency=concurrency)

    if not skip_baseline:
        raw_gen = generate_all(generator, RAW_SYSTEM_PROMPT, pool, concurrency=concurrency)
        raw_pw = run_pairwise(judge, pool, raw_gen, seed=seed, concurrency=concurrency)
        baselines["raw_model"] = _indist(raw_pw)
        baseline_delta["vs_raw_model"] = _delta(headline_pw.score, raw_pw.score)

    now = datetime.now(UTC)
    report = FidelityReport(
        persona=f"{persona_id}@{now.strftime('%Y.%m')}.0",
        model=generator.model,
        rubric_version=rubric.version,
        n_test=headline_pw.n_pairs,
        condition=condition,
        indistinguishability=_indist(headline_pw),
        dimensions=dims,
        judge=JudgeInfo(model=judge.model),
        baseline_delta=baseline_delta,
        baselines=baselines,
        diagnostics={
            "position_bias": headline_pw.position_bias,
            "mean_real_len": headline_pw.mean_real_len,
            "mean_generated_len": headline_pw.mean_generated_len,
            "eligible_test_traces": len(eligible_pairwise_traces(traces, split="test")),
            "seed": seed,
            "cost": cost_tracker.snapshot(),
        },
        timestamp=now.isoformat(),
    )
    fidelity_dir = persona_dir / "evals" / "fidelity"
    fidelity_dir.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime("%Y-%m-%d")
    if condition == "compiled":
        stamp += "-compiled"
    path = fidelity_dir / f"{stamp}.json"
    path.write_text(report.model_dump_json(indent=2) + "\n")
    (fidelity_dir / "latest.json").write_text(
        json.dumps({"latest": path.name, "timestamp": report.timestamp}, indent=2) + "\n"
    )
    export_calibration(persona_dir, stamp, pool, headline_gen, headline_pw.pairs, seed=seed)
    return report, path
