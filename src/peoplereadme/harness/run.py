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
from .lm import LM
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


def generate_all(lm: LM, system_prompt: str, traces: list[Trace]) -> dict[str, str]:
    return {t.id: lm.complete(system_prompt, behavior_prompt(t)) for t in traces}


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
) -> tuple[FidelityReport, Path]:
    """Run the M2 harness; writes evals/fidelity/{date}.json + a calibration batch."""
    rubric = load_rubric(persona_dir)
    traces = load_traces(persona_dir)
    pool = eligible_pairwise_traces(traces, split="test")
    rng = random.Random(seed)
    if len(pool) > n_pairs:
        pool = rng.sample(pool, n_pairs)

    package_prompt = package_as_prompt(persona_dir)
    package_gen = generate_all(generator, package_prompt, pool)
    package_pw = run_pairwise(judge, pool, package_gen, seed=seed)
    dims = score_dimensions(judge, rubric, pool, package_gen)

    baselines: dict[str, Indistinguishability] = {}
    baseline_delta: dict[str, str] = {}
    if not skip_baseline:
        raw_gen = generate_all(generator, RAW_SYSTEM_PROMPT, pool)
        raw_pw = run_pairwise(judge, pool, raw_gen, seed=seed)
        baselines["raw_model"] = _indist(raw_pw)
        baseline_delta["vs_raw_model"] = _delta(package_pw.score, raw_pw.score)

    now = datetime.now(UTC)
    report = FidelityReport(
        persona=f"{persona_id}@{now.strftime('%Y.%m')}.0",
        model=generator.model,
        rubric_version=rubric.version,
        n_test=package_pw.n_pairs,
        condition="package",
        indistinguishability=_indist(package_pw),
        dimensions=dims,
        judge=JudgeInfo(model=judge.model),
        baseline_delta=baseline_delta,
        baselines=baselines,
        diagnostics={
            "position_bias": package_pw.position_bias,
            "mean_real_len": package_pw.mean_real_len,
            "mean_generated_len": package_pw.mean_generated_len,
            "eligible_test_traces": len(eligible_pairwise_traces(traces, split="test")),
            "seed": seed,
        },
        timestamp=now.isoformat(),
    )
    fidelity_dir = persona_dir / "evals" / "fidelity"
    fidelity_dir.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime("%Y-%m-%d")
    path = fidelity_dir / f"{stamp}.json"
    path.write_text(report.model_dump_json(indent=2) + "\n")
    (fidelity_dir / "latest.json").write_text(
        json.dumps({"latest": path.name, "timestamp": report.timestamp}, indent=2) + "\n"
    )
    export_calibration(persona_dir, stamp, pool, package_gen, package_pw.pairs, seed=seed)
    return report, path
