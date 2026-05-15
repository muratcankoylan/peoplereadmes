# Architecture

peoplereadmes stores each persona as a structured context system, not as a single long prompt.

The architecture is designed for open-source use: contributors should be able to inspect the research trail, understand how synthesis happened, load only the files needed for a task, and fork the framework for another public builder or creative.

## Design Goals

- Make personas usable by both humans and agents.
- Keep context modular so agents load only what they need.
- Preserve provenance and uncertainty.
- Separate direct evidence from interpretation.
- Prevent identity impersonation and private psychological claims.
- Include safety and evaluation as first-class artifacts.
- Make the framework forkable for new public figures.

## Core Pipeline

```text
public evidence
-> source inventory
-> project catalog
-> quote bank
-> evidence map
-> context modules
-> prompts
-> rubrics
-> examples
```

The pipeline exists to stop persona work from becoming vibes-only prompting. Research is preserved as raw material, then transformed into modular artifacts that can be inspected and evaluated.

## Artifact Layers

### Research Layer

Stores raw research outputs and notes.

Examples:

- `personas/riley-walz/research/deep-dive/`
- `personas/riley-walz/research/technical-deep-dive/`

This layer is evidence material. It should not be treated as the final context model.

### Data Layer

Stores machine-readable facts, sources, and synthesis anchors.

Core files:

- `data/projects.json`
- `data/sources.json`
- `data/heuristics.json`
- `data/quote-bank.json`
- `data/evidence-map.json`
- `data/technical-ability-model.json`

The data layer should make claims traceable and reusable by agents.

### Context Layer

Stores human-readable synthesis modules.

Core files:

- `context/context-pack.md`
- `context/brain-model.md`
- `context/idea-engine.md`
- `context/taste-and-voice.md`
- `context/technical-playbook.md`
- `context/advanced-technical-intelligence.md`
- `context/safety-boundaries.md`

The context layer is what agents usually load.

### Prompt Layer

Stores agent instructions.

Core files:

- `prompts/system-prompt.md`
- `prompts/deep-context-system.md`
- `prompts/task-modes.md`

Prompts must remain non-impersonating.

### Evaluation Layer

Stores rubrics and review criteria.

Core files:

- `evals/rubric.md`
- `evals/brain-model-rubric.md`

Evaluation should test evidence fidelity, technical plausibility, non-impersonation, uncertainty handling, safety, and practical usefulness.

### Agent Layer

Stores repo-level agents that help people use or audit the framework.

Current agent:

- `agents/project-navigator-agent.md`

The navigator agent routes users to the right files, explains the synthesis method, and helps contributors fork the repo for new persona packages.

### Governance Layer

Stores repo-level files that govern how the project is licensed, contributed to, secured, cited, and discovered by agents. These files are not specific to any persona; they define the project surface visible to humans, package registries, GitHub, and AI agents.

Core files:

- `LICENSE`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `CITATION.cff`
- `llms.txt`

`LICENSE` and `CITATION.cff` are referenced from `manifest.json`. `CONTRIBUTING.md` carries the new-persona checklist that agents and human contributors both load when forking. `SECURITY.md` documents the private advisory channel for safety violations and complements the per-persona `context/safety-boundaries.md`. `llms.txt` follows the llmstxt.org convention so agents can find the canonical entry points without crawling.

## Persona Package Layout

Minimum package:

```text
personas/{persona-id}/
  README.md
  context/
    context-pack.md
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

Deep package:

```text
personas/{persona-id}/
  context/
    brain-model.md
    idea-engine.md
    taste-and-voice.md
    technical-playbook.md
    advanced-technical-intelligence.md
  data/
    quote-bank.json
    evidence-map.json
    technical-ability-model.json
  research/
    deep-dive/
    technical-deep-dive/
```

## Load Profiles

### Quick Agent

Use:

- `context/context-pack.md`
- `prompts/system-prompt.md`
- `context/safety-boundaries.md`

### Ideation

Use:

- `context/context-pack.md`
- `context/brain-model.md`
- `context/idea-engine.md`
- `context/tacit-knowledge.md`
- `context/project-patterns.md`
- `prompts/task-modes.md`

### Technical Analysis

Use:

- `context/technical-playbook.md`
- `context/advanced-technical-intelligence.md`
- `data/technical-ability-model.json`
- `research/technical-deep-dive/README.md`

### Project Review

Use:

- `context/project-patterns.md`
- `context/safety-boundaries.md`
- `evals/rubric.md`
- `evals/brain-model-rubric.md`

### Factual Lookup

Use:

- `data/projects.json`
- `data/heuristics.json`
- `data/sources.json`
- `data/quote-bank.json`
- `data/evidence-map.json`

### Repo Navigation

Use:

- `agents/project-navigator-agent.md`
- `README.md`
- `manifest.json`
- `docs/architecture.md`
- `LICENSE`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `CITATION.cff`
- `llms.txt`

## Synthesis Standards

Each synthesized claim should answer:

- What public evidence supports this?
- Is it direct evidence or inference?
- Which source tier does it come from?
- How confident are we?
- What are the limitations?
- What safety risks appear if this is operationalized?

## Maintenance Rules

- Do not add private data.
- Add a source entry for each factual claim.
- Add a risk note for each project.
- Keep prompts non-impersonating.
- Keep raw research separate from curated context.
- Keep safety boundaries explicit.
- Validate machine-readable files against `schemas/persona.schema.json` where applicable.
- Update `manifest.json` when adding personas or repo-level agents.
