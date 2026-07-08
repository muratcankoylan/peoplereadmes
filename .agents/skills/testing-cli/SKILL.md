---
name: testing-cli
description: How to test the peoplereadme CLI end-to-end, including the fidelity harness (eval/calibrate) with a synthetic persona fixture and live LLM calls.
---

# Testing the peoplereadme CLI

All testing is shell-only (no GUI). Use a clean clone + `uv sync`, then `uv run peoplereadme ...`.

## Basic checks
- `uv run ruff check src tests` and `uv run pytest -q` (all tests offline, no API keys needed).
- `uv run peoplereadme validate` must exit 0 (riley-walz must stay schema-valid).

## Synthetic persona fixture (for ingest/trace/eval testing)
1. `uv run peoplereadme init me --class self`
2. Build a synthetic X export zip: `data/account.js` + `data/tweets.js` with `window.YTD.account.part0 = [...]` / `window.YTD.tweets.part0 = [...]` prefixes; tweets are `{"tweet": {"id_str", "full_text", "created_at": "%a %b %d %H:%M:%S +0000 %Y", ...}}`. Self-threads (replies to own tweets via `in_reply_to_status_id_str`) produce traces with reconstruction_quality 0.8; standalone posts get 0.2 (both pairwise-eligible; the harness excludes < 0.2). Use ~40 tweets so the 15% test split has ≥5 eligible traces.
3. `uv run peoplereadme ingest me --source x-archive=archive.zip` then `uv run peoplereadme trace me`.

## Harness (M2) live testing
- Requires `OPENAI_API_KEY` (available as a saved Devin secret). Use `--model openai/gpt-4o-mini` and small `--n-pairs` (e.g. 6) to keep cost < $1; a 6-pair run with baseline takes ~70s.
- `uv run peoplereadme eval me --model openai/gpt-4o-mini --n-pairs 6 --seed 7` writes `personas/me/evals/fidelity/<date>.json`, auto-creates `evals/rubrics/v1.json`, and exports a blind calibration batch to `evals/fidelity/calibration/<date>.jsonl` (+ private `<date>.answers.json` key).
- Judge calls are disk-cached in `~/.peoplereadme/cache/llm` (override root with `PEOPLEREADME_CACHE`); delete to force fresh judging.
- Calibration roundtrip: fill `human_pick` ("A"/"B") in the blind JSONL, then `uv run peoplereadme calibrate me --batch <date> --ratings rated.jsonl`. Expect exit 1 with "INVALID report card" whenever kappa < 0.4 or fewer than 50 rated pairs — that hard floor firing is correct behavior, not a bug.
- Expected diagnostics gotcha: with a skeleton persona package (no real context files) the judge often scores below chance and generated outputs are far longer than real tweets — check `diagnostics` in fidelity.json (position_bias, mean_real_len, mean_generated_len).

## Failure modes (should all be clean errors, exit 1, no tracebacks)
- eval on a persona without `traces/traces.jsonl`
- calibrate with a missing batch/answers key
- eval with an invalid API key (LMError path)
