"""Human calibration flow (PRD 9.5).

Every report card requires a human calibration batch: >= 50 pairs rated by a
human, Cohen's kappa judge-vs-human reported, kappa < 0.4 invalidates the card.

Flow:
1. `export_calibration` writes evals/fidelity/calibration/{batch}.jsonl — blind
   pairs (position-randomized, no answers) for a human to rate — plus a private
   {batch}.answers.json holding truth positions and judge picks.
2. The human fills in "human_pick" ("A" or "B") on each JSONL line.
3. `import_calibration` joins ratings with the answer key and computes kappa
   between judge picks and human picks over the same items.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from pydantic import BaseModel

from ..models import Trace
from .pairwise import PairResult
from .stats import cohens_kappa

KAPPA_HARD_FLOOR = 0.4
MIN_CALIBRATION_PAIRS = 50


class CalibrationResult(BaseModel):
    batch: str
    n_pairs: int
    kappa: float
    valid: bool
    human_accuracy: float


def calibration_dir(persona_dir: Path) -> Path:
    return persona_dir / "evals" / "fidelity" / "calibration"


def export_calibration(
    persona_dir: Path,
    batch: str,
    traces: list[Trace],
    generations: dict[str, str],
    pair_results: list[PairResult],
    seed: int = 0,
) -> tuple[Path, Path]:
    """Write blind rating file + private answer key. Returns (blind, key) paths."""
    by_id = {t.id: t for t in traces}
    rng = random.Random(seed)
    directory = calibration_dir(persona_dir)
    directory.mkdir(parents=True, exist_ok=True)
    blind_path = directory / f"{batch}.jsonl"
    key_path = directory / f"{batch}.answers.json"
    key: dict[str, dict] = {}
    with blind_path.open("w") as fh:
        for result in pair_results:
            trace = by_id.get(result.trace_id)
            generated = generations.get(result.trace_id)
            if trace is None or generated is None:
                continue
            real_first = rng.random() < 0.5
            a, b = (
                (trace.behavior.content, generated)
                if real_first
                else (generated, trace.behavior.content)
            )
            fh.write(
                json.dumps(
                    {
                        "pair_id": result.trace_id,
                        "kind": trace.kind,
                        "context": trace.context.content,
                        "candidate_a": a,
                        "candidate_b": b,
                        "human_pick": None,
                    }
                )
                + "\n"
            )
            # Judge pick mapped onto this batch's positions: judge "picked real"
            # iff correct > 0.5; inconsistent judgments (0.5) count as picking
            # the position the human will compare against at random.
            judge_picked_real = result.correct > 0.5 or (
                result.correct == 0.5 and rng.random() < 0.5
            )
            real_pos = "A" if real_first else "B"
            other = "B" if real_first else "A"
            key[result.trace_id] = {
                "real": real_pos,
                "judge_pick": real_pos if judge_picked_real else other,
            }
    key_path.write_text(json.dumps(key, indent=2) + "\n")
    return blind_path, key_path


def import_calibration(persona_dir: Path, batch: str, ratings_path: Path) -> CalibrationResult:
    key = json.loads((calibration_dir(persona_dir) / f"{batch}.answers.json").read_text())
    judge_picks: list[str] = []
    human_picks: list[str] = []
    correct_humans = 0
    for line in ratings_path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        pick = row.get("human_pick")
        entry = key.get(row.get("pair_id"))
        if entry is None or pick not in ("A", "B"):
            continue
        judge_picks.append(entry["judge_pick"])
        human_picks.append(pick)
        if pick == entry["real"]:
            correct_humans += 1
    if not human_picks:
        raise ValueError("no rated pairs found (fill in human_pick as 'A' or 'B')")
    kappa = round(cohens_kappa(judge_picks, human_picks), 4)
    n = len(human_picks)
    return CalibrationResult(
        batch=batch,
        n_pairs=n,
        kappa=kappa,
        valid=kappa >= KAPPA_HARD_FLOOR and n >= MIN_CALIBRATION_PAIRS,
        human_accuracy=round(correct_humans / n, 4),
    )
