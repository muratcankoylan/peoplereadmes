---
name: testing-peoplereadme-cli
description: Set up and end-to-end test the peoplereadme CLI (init, validate, schema changes). Use when verifying changes to src/peoplereadme/, schemas/persona.schema.json, or persona package scaffolding.
---

# Testing the peoplereadme CLI

## Setup
- Python 3.12+ and uv are required. `uv sync --dev` from the repo root installs everything (typer, pydantic, jsonschema, pytest, ruff) and the `peoplereadme` entrypoint.
- Test in a clean clone (e.g. `git clone -b <branch> <repo> /tmp/prtest`) so `init` runs don't dirty the working repo — `init` mutates `manifest.json` and creates `personas/{id}/`.
- All testing is shell-only; no browser/recording needed.

## Core commands
- Lint: `uv run ruff check src tests`
- Unit tests: `uv run pytest -q`
- Schema validation of all personas: `uv run peoplereadme validate` (validates `personas/*/persona.json` against `schemas/persona.schema.json`; legacy packages without persona.json are skipped)
- Version: `uv run peoplereadme --version`

## End-to-end checks worth repeating
1. `uv run peoplereadme init <id> --class other` → expect exit 0 and "Schema validation passed."; verify skeleton dirs (`context/ data/ prompts/ evals/rubrics/ evals/fidelity/ evidence/ traces/ compiled/ exports/`), `evidence/sources.lock`, `traces/splits.json`, a `persona.json` with `class=other`, no `consent`, no `voice` in `allowed_exports`, non-affiliation header in README, and exactly one new `manifest.json` entry.
2. `--class self` → `consent` object present, `voice` in `allowed_exports`, `evidence/.gitignore` ignoring `*.jsonl`.
3. Adversarial: set `"class": "fan-fiction"` in a persona.json and run `validate <id>` — must exit 1 citing the enum. If it passes, schema enforcement is broken.
4. Regression: after any schema change, `uv run pytest tests/test_schema.py -q` proves the Riley package still validates unchanged; also `git status` should show no changes under `personas/riley-walz/`.

## Known quirks
- Duplicate `init <id>` errors with a raw typer traceback (FileExistsError) rather than a clean message — this might be improved later; nonzero exit and no duplicate manifest entry are the assertions that matter.
- `validate` run outside a repo root fails with "Not inside a peoplereadmes repo"; run from the repo root (it walks upward looking for manifest.json + schemas/persona.schema.json).

## Devin Secrets Needed
- None for CLI/schema testing (all local, no network). Later pipeline stages (compile/eval) will need LLM provider keys via env (e.g. OPENAI_API_KEY or similar litellm-compatible keys).
