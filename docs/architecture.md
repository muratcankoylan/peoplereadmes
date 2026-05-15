# Architecture

PersonaTheAutism stores each persona as a structured context system, not as a single long prompt.

## Design Goals

- Make personas usable by both humans and agents.
- Keep context modular so agents load only what they need.
- Preserve provenance and uncertainty.
- Prevent identity impersonation and private psychological claims.
- Include safety and evaluation as first-class artifacts.

## Persona Package Layout

```text
personas/{persona-id}/
  README.md
  context/
    context-pack.md
    tacit-knowledge.md
    project-patterns.md
    safety-boundaries.md
  prompts/
    system-prompt.md
    task-modes.md
  data/
    projects.json
    heuristics.json
    sources.json
  evals/
    rubric.md
  examples/
    project-brief.md
```

## Load Profiles

### Quick Agent

Use:

- `context/context-pack.md`
- `prompts/system-prompt.md`

### Ideation

Use:

- `context/context-pack.md`
- `context/tacit-knowledge.md`
- `context/safety-boundaries.md`
- `prompts/task-modes.md`

### Project Review

Use:

- `context/project-patterns.md`
- `context/safety-boundaries.md`
- `evals/rubric.md`

### Factual Lookup

Use:

- `data/projects.json`
- `data/heuristics.json`
- `data/sources.json`

## Maintenance Rules

- Do not add private data.
- Add a source entry for each factual claim.
- Add a risk note for each project.
- Keep prompts non-impersonating.
- Validate machine-readable files against `schemas/persona.schema.json`.
