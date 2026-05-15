# Contributing

This project models public professional patterns. Contributions should preserve the evidence-bound, non-impersonating design.

## Good contributions

- Add public sources with provenance.
- Improve claim support in `data/evidence-map.json`.
- Add missing safety caveats.
- Improve schema consistency against `schemas/persona.schema.json`.
- Add better examples in `personas/<id>/examples/`.
- Expand rubrics in `personas/<id>/evals/`.
- Add a new persona package with clear evidence boundaries.

## Bad contributions

- Private or invasive information.
- Unverified gossip.
- First-person impersonation prompts.
- Instructions for evading platform controls.
- Data harvesting recipes for sensitive sources.
- Claims that cannot be traced back to public evidence.

## New persona checklist

Before opening a PR for a new persona, the package must include:

- `README.md`
- `context/context-pack.md`
- `context/safety-boundaries.md`
- `prompts/system-prompt.md`
- `prompts/task-modes.md`
- `data/projects.json`
- `data/sources.json`
- `data/heuristics.json`
- `evals/rubric.md`
- An entry in `manifest.json`

For deep packages, also add:

- `context/brain-model.md`
- `context/idea-engine.md`
- `context/taste-and-voice.md`
- `context/technical-playbook.md`
- `data/quote-bank.json`
- `data/evidence-map.json`
- A `research/` directory with raw research outputs or notes.

## PR shape

- One purpose per PR.
- Reference evidence sources in the PR description for any new factual claim.
- Note safety implications when relevant.
- Validate machine-readable files against `schemas/persona.schema.json` where applicable.
- Update `manifest.json` when adding personas or repo-level agents.

## Reporting safety issues

See `SECURITY.md` for the private advisory channel, in-scope and out-of-scope categories, and response timeline.
