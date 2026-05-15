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
- `context/tacit-knowledge.md` for thinking patterns and decision heuristics.
- `data/projects.json` for a machine-readable project catalog.
- `prompts/system-prompt.md` and `prompts/task-modes.md` for agent setup.
- `evals/rubric.md` for output review.

## Principles

- Use public or consented sources only.
- Separate evidence from inference.
- Model professional patterns, not private psychology.
- Never claim to speak as the person.
- Include safety boundaries and evaluation rubrics with every persona.
