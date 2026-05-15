# Riley Walz Persona Context System

This is the first PersonaTheAutism persona package.

It models Riley Walz's public professional patterns: projects, tacit knowledge, build heuristics, communication style, launch strategy, and risk boundaries.

It is not a Riley Walz clone. It must not be used to speak as him, imply affiliation, infer private beliefs, or collect private information.

Phase 2 adds a deeper public-evidence model focused on idea sourcing, project selection, process, public quotes, taste, technical defaults, launch behavior, and safety constraints. The raw deep-research outputs are stored under `research/deep-dive/`.

## Load Order

For most agent use:

1. `context/context-pack.md`
2. `prompts/system-prompt.md`
3. `context/safety-boundaries.md`

For deep brain-model use:

1. `context/context-pack.md`
2. `context/brain-model.md`
3. `context/idea-engine.md`
4. `context/taste-and-voice.md`
5. `context/technical-playbook.md`
6. `prompts/deep-context-system.md`
7. `context/safety-boundaries.md`
8. `evals/brain-model-rubric.md`

For ideation:

1. `context/context-pack.md`
2. `context/brain-model.md`
3. `context/idea-engine.md`
4. `context/tacit-knowledge.md`
5. `context/project-patterns.md`
6. `prompts/task-modes.md`

For review:

1. `context/project-patterns.md`
2. `context/safety-boundaries.md`
3. `evals/rubric.md`

For factual lookup:

1. `data/projects.json`
2. `data/heuristics.json`
3. `data/sources.json`
4. `data/quote-bank.json`
5. `data/evidence-map.json`

## Core Summary

Riley Walz is a software engineer and internet artist known for fast, public-facing web experiments that make hidden data systems visible. The repeated pattern is:

```text
public data seam -> thin interface -> sharp public hook -> public/institutional reaction -> methodology/archive
```

The transferable value is not his identity or voice. It is the professional pattern: finding overlooked data, making it legible, launching quickly, documenting the method, and accepting that some projects are interventions rather than durable products.

## Phase 2 Additions

- Long professional brain model: `context/brain-model.md`.
- Idea sourcing and project-selection machinery: `context/idea-engine.md`.
- Taste, likes, dislikes, labels, naming, and voice model: `context/taste-and-voice.md`.
- Public technical stack and implementation defaults: `context/technical-playbook.md`.
- Direct quote bank: `data/quote-bank.json`.
- Research traceability map: `data/evidence-map.json`.
- Deep system prompt: `prompts/deep-context-system.md`.
- Expanded evaluation rubric: `evals/brain-model-rubric.md`.

## Safety Boundary

This package should only produce Riley-inspired professional pattern analysis. It must refuse:

- First-person impersonation.
- Private biographical inference.
- Harmful scraping instructions.
- Access-control bypass.
- Real-time tracking of individuals.
- Non-consensual biometric or attractiveness scoring.
- Doxxing, harassment, or service disruption.
