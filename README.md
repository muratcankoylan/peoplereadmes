# PersonaTheAutism

Structured persona context systems for studying exceptional public thinkers and builders.

This repository stores evidence-bound, non-impersonating context packs. Each persona package should help people and agents understand public professional patterns, tacit knowledge, projects, operating heuristics, and safety boundaries.

The first persona package is Riley Walz.

## Repository Structure

```text
personas/
  riley-walz/
    README.md
    context/
    prompts/
    data/
    evals/
    examples/
schemas/
docs/
```

## How To Use

Start with `personas/riley-walz/README.md`, then load only the files required for the task:

- `context/context-pack.md` for a compact default agent context.
- `context/brain-model.md` for the long-form public professional brain model.
- `context/idea-engine.md` for idea sourcing, project selection, and process simulation.
- `context/taste-and-voice.md` for naming, tone, likes, dislikes, and public framing.
- `context/technical-playbook.md` for public technical defaults and safe implementation patterns.
- `context/tacit-knowledge.md` for thinking patterns and decision heuristics.
- `data/projects.json` for a machine-readable project catalog.
- `data/quote-bank.json` and `data/evidence-map.json` for evidence-grounded usage.
- `prompts/system-prompt.md` and `prompts/task-modes.md` for agent setup.
- `prompts/deep-context-system.md` for deep context loading.
- `evals/rubric.md` and `evals/brain-model-rubric.md` for output review.

## Principles

- Use public or consented sources only.
- Separate evidence from inference.
- Model professional patterns, not private psychology.
- Never claim to speak as the person.
- Include safety boundaries and evaluation rubrics with every persona.
