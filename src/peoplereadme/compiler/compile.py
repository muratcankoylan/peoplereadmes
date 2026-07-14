"""Compile orchestration: seed program -> optimize -> save auditable artifact.

Optimizers (PRD 10, DSPy 3.x):
- none: seeded program only (deterministic; the uncompiled baseline).
- bootstrap: BootstrapFewShot — cheap demo selection from the train split.
- gepa: reflective instruction evolution (primary). Uses a separate reflection
  LM and the judge-backed feedback metric; validates on the dev split.

Artifacts land in compiled/: program.json (DSPy state, diffable), and
compile.lock.json (models, optimizer, dataset counts/hashes, dev scores).
Test traces are never loaded here.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import dspy
from pydantic import BaseModel, Field

from .. import __version__
from ..harness.lm import LM
from ..harness.run import load_traces
from .data import build_datasets
from .metric import as_float_metric, make_feedback_metric
from .program import PersonaProgram, persona_brief, seed_instructions

MIN_TRAIN_EXAMPLES = 4
LM_MAX_TOKENS = 16_000


class CompileResult(BaseModel):
    persona: str
    optimizer: str
    task_model: str
    reflection_model: str | None = None
    judge_model: str
    n_train: int
    n_dev: int
    dataset_hash: str
    seed_dev_score: float | None = None
    compiled_dev_score: float | None = None
    dspy_version: str
    peoplereadme_version: str
    timestamp: str
    program_path: str
    metadata: dict = Field(default_factory=dict)


def build_task_lm(model: str) -> dspy.LM:
    # gpt-5.x reject non-default temperature; reasoning models need large budgets.
    return dspy.LM(model, temperature=1.0, max_tokens=LM_MAX_TOKENS)


def _dataset_hash(examples: list[dspy.Example]) -> str:
    payload = "\x00".join(e.trace_id for e in examples)
    return f"sha256:{hashlib.sha256(payload.encode()).hexdigest()}"


def _mean_dev_score(program: dspy.Module, devset: list[dspy.Example], metric) -> float:
    if not devset:
        return 0.0
    scores = [metric(ex, program(task=ex.task, context=ex.context)).score for ex in devset]
    return round(sum(scores) / len(scores), 4)


def run_compile(
    persona_dir: Path,
    persona_id: str,
    judge: LM,
    task_model: str,
    reflection_model: str | None = None,
    optimizer: str = "gepa",
    auto: str = "light",
    seed: int = 0,
    max_train: int | None = None,
    max_dev: int | None = None,
    skip_dev_scores: bool = False,
) -> CompileResult:
    traces = load_traces(persona_dir)
    trainset, devset = build_datasets(traces, max_train=max_train, max_dev=max_dev)
    if len(trainset) < MIN_TRAIN_EXAMPLES:
        raise ValueError(
            f"only {len(trainset)} eligible train examples "
            f"(need >= {MIN_TRAIN_EXAMPLES}; run ingest/trace on more evidence)"
        )
    if optimizer == "gepa" and not devset:
        raise ValueError("GEPA needs a non-empty dev split for validation")

    brief = persona_brief(persona_dir)
    draft_seed, refine_seed = seed_instructions(
        [t for t in traces if t.split == "train"]
    )
    program = PersonaProgram(brief, draft_seed, refine_seed)
    metric = make_feedback_metric(judge)

    seed_score = None if skip_dev_scores else _mean_dev_score(program, devset, metric)

    if optimizer == "none":
        compiled = program
    elif optimizer == "bootstrap":
        boot = dspy.BootstrapFewShot(
            metric=as_float_metric(metric), max_bootstrapped_demos=4, max_labeled_demos=4
        )
        compiled = boot.compile(program, trainset=trainset)
    elif optimizer == "gepa":
        if not reflection_model:
            raise ValueError("GEPA requires --reflection-model")
        log_dir = persona_dir / "compiled" / "gepa_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        gepa = dspy.GEPA(
            metric=metric,
            auto=auto,
            reflection_lm=build_task_lm(reflection_model),
            track_stats=True,
            log_dir=str(log_dir),
            seed=seed,
        )
        compiled = gepa.compile(program, trainset=trainset, valset=devset)
    else:
        raise ValueError(f"unknown optimizer {optimizer!r} (none | bootstrap | gepa)")

    compiled_score = (
        seed_score
        if optimizer == "none"
        else (None if skip_dev_scores else _mean_dev_score(compiled, devset, metric))
    )

    compiled_dir = persona_dir / "compiled"
    compiled_dir.mkdir(parents=True, exist_ok=True)
    program_path = compiled_dir / "program.json"
    compiled.save(str(program_path))

    result = CompileResult(
        persona=persona_id,
        optimizer=optimizer,
        task_model=task_model,
        reflection_model=reflection_model if optimizer == "gepa" else None,
        judge_model=judge.model,
        n_train=len(trainset),
        n_dev=len(devset),
        dataset_hash=_dataset_hash(trainset + devset),
        seed_dev_score=seed_score,
        compiled_dev_score=compiled_score,
        dspy_version=dspy.__version__,
        peoplereadme_version=__version__,
        timestamp=datetime.now(UTC).isoformat(),
        program_path=str(program_path.relative_to(persona_dir)),
        metadata={
            "auto": auto if optimizer == "gepa" else None,
            "seed": seed,
            "brief_hash": f"sha256:{hashlib.sha256(brief.encode()).hexdigest()}",
            "brief_chars": len(brief),
            "modules": ["draft", "refine"],
        },
    )
    (compiled_dir / "compile.lock.json").write_text(result.model_dump_json(indent=2) + "\n")
    return result
