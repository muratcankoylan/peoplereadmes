# peoplereadmes

Open-source persona context systems for studying exceptional public builders, artists, researchers, and creative operators.

This repository is not a celebrity chatbot project. It is a framework for turning public evidence into structured, non-impersonating context systems that help humans and agents understand how a person works: what they build, how they find ideas, which constraints shape their taste, what technical patterns repeat, which risks appear, and how to evaluate outputs that claim to be inspired by them.

The first persona package is `personas/riley-walz/`.

## What This Project Is

peoplereadmes is a research and synthesis framework.

For each public figure, the repo should preserve:

- Public source material and research outputs.
- A compact context pack for normal agent use.
- Long-form thinking, process, and technical models.
- Machine-readable data files for projects, sources, quotes, and heuristics.
- Prompts that tell agents how to use the context without impersonating the person.
- Rubrics that test whether generated outputs are faithful, useful, safe, and evidence-bound.
- Safety boundaries that prevent private inference, identity simulation, doxxing, harmful scraping, or other misuse.

The goal is to help more people learn from unusually creative builders without pretending to be them.

## Why It Exists

Most "persona" systems are shallow. They collect biographical facts, summarize tone, and ask an LLM to imitate a person. That is not enough for serious creative or technical work.

This project takes a different approach:

```text
public evidence -> source map -> project analysis -> tacit-knowledge extraction -> technical model -> prompt system -> eval rubric -> reusable context package
```

The useful object is not a clone of a person. The useful object is a structured model of observable professional patterns:

- How they notice opportunities.
- How they choose projects.
- How they compress complex ideas into public artifacts.
- How they use tools, APIs, data, hardware, or interfaces.
- How they launch, explain, and archive work.
- Which risks and ethical boundaries repeat.

For Riley Walz, that means studying the public pattern behind projects like `Bop Spotter`, `IMG_0001`, `Find My Parking Cops`, `Library Spy`, `Amtrak Right Now`, `Payphone Go`, and `Jmail`: public data seams, thin interfaces, sharp hooks, rapid builds, explicit caveats, and institutional or cultural reaction.

## What This Is Not

This repo must not be used to:

- Speak as another person.
- Claim endorsement, affiliation, or access to private thoughts.
- Infer private psychology, relationships, home details, private work, or private communications.
- Build doxxing, harassment, evasion, credential misuse, or access-control bypass workflows.
- Publish harmful instructions for scraping, tracking, biometric scoring, or social profiling.
- Treat "publicly accessible" as automatic ethical permission.

Every persona package should preserve the difference between evidence, interpretation, and generated inspiration.

## Repository Structure

```text
agents/
  project-navigator-agent.md
docs/
  architecture.md
personas/
  riley-walz/
    README.md
    context/
    data/
    evals/
    examples/
    prompts/
    research/
schemas/
  persona.schema.json
manifest.json
README.md
```

## The Riley Walz Package

The current package models Riley Walz's public professional patterns.

Start here:

- `personas/riley-walz/README.md` explains the package and load order.
- `personas/riley-walz/context/context-pack.md` is the compact default context.
- `personas/riley-walz/context/brain-model.md` is the long-form professional pattern model.
- `personas/riley-walz/context/idea-engine.md` models idea discovery and project selection.
- `personas/riley-walz/context/taste-and-voice.md` models taste, framing, naming, likes, and dislikes.
- `personas/riley-walz/context/technical-playbook.md` summarizes technical defaults.
- `personas/riley-walz/context/advanced-technical-intelligence.md` models public API/data-seam discovery instincts and technical operator patterns.
- `personas/riley-walz/context/safety-boundaries.md` defines hard boundaries.
- `personas/riley-walz/data/projects.json` is the project catalog.
- `personas/riley-walz/data/heuristics.json` is the machine-readable heuristic set.
- `personas/riley-walz/data/technical-ability-model.json` structures the deeper technical ability analysis.
- `personas/riley-walz/data/quote-bank.json` stores direct public quotes.
- `personas/riley-walz/data/evidence-map.json` links claims back to research runs and source tiers.
- `personas/riley-walz/prompts/system-prompt.md` is the standard agent prompt.
- `personas/riley-walz/prompts/deep-context-system.md` is the full deep-context prompt.
- `personas/riley-walz/evals/rubric.md` and `personas/riley-walz/evals/brain-model-rubric.md` evaluate output quality.

Raw deep research is stored under:

- `personas/riley-walz/research/deep-dive/`
- `personas/riley-walz/research/technical-deep-dive/`

These research files are intentionally kept separate from the synthesized context files. Raw research is evidence material; context files are the curated model.

## How To Use This Repo

### 1. Use the Existing Riley Package

For a fast agent setup, load:

```text
personas/riley-walz/context/context-pack.md
personas/riley-walz/prompts/system-prompt.md
personas/riley-walz/context/safety-boundaries.md
```

For deep analysis, load:

```text
personas/riley-walz/context/context-pack.md
personas/riley-walz/context/brain-model.md
personas/riley-walz/context/idea-engine.md
personas/riley-walz/context/taste-and-voice.md
personas/riley-walz/context/technical-playbook.md
personas/riley-walz/context/advanced-technical-intelligence.md
personas/riley-walz/prompts/deep-context-system.md
personas/riley-walz/context/safety-boundaries.md
personas/riley-walz/evals/brain-model-rubric.md
```

For factual lookup, load:

```text
personas/riley-walz/data/projects.json
personas/riley-walz/data/heuristics.json
personas/riley-walz/data/sources.json
personas/riley-walz/data/quote-bank.json
personas/riley-walz/data/evidence-map.json
```

### 2. Ask the Project Navigator Agent

Use `agents/project-navigator-agent.md` when you want an agent to inspect the repo and send the right files for your task.

Example tasks:

```text
Explain how this repo synthesizes deep research into context files.
Send me the minimum files needed to use the Riley Walz persona for ideation.
Analyze the technical ability framework and tell me how to adapt it for another builder.
Help me fork this repo and create a new persona package for a favorite creative.
Review the rubric system and suggest improvements.
```

### 3. Fork It For Another Builder

Create a new folder:

```text
personas/{person-id}/
```

Use the Riley package as the reference implementation, then build the new package in stages:

1. Define the identity boundary and allowed use.
2. Collect public sources only.
3. Build `data/sources.json`.
4. Build `data/projects.json`.
5. Extract direct quotes into `data/quote-bank.json`.
6. Write `context/context-pack.md`.
7. Write deeper modules for ideas, tacit knowledge, taste, technical patterns, and safety.
8. Create prompts for normal and deep agent use.
9. Add evaluation rubrics.
10. Add the new persona to `manifest.json`.

Do not start with a prompt. Start with evidence.

## Research Method

The research process has four layers.

### 1. Source Collection

Collect public artifacts:

- First-party websites.
- Public project pages.
- Public GitHub repositories.
- Public talks, interviews, podcasts, and transcripts.
- Public posts and launch threads.
- Press coverage.
- Public datasets and documentation.
- Archived project pages.
- Forum comments where the person or technical readers add detail.

Private sources are out of scope. Paywalled sources should be summarized only when access is lawful and citation constraints are respected.

### 2. Evidence Mapping

Every claim should be traceable.

Use files like:

- `data/sources.json` for source inventory.
- `data/evidence-map.json` for claim support, source tiers, limitations, and research runs.
- `data/quote-bank.json` for exact public quotes.
- Raw `research/` outputs for deeper basis material.

The project should make it obvious when a statement is:

- Direct evidence.
- A cross-source synthesis.
- A model inference.
- A speculative hypothesis.
- A safety caveat.

### 3. Synthesis

Synthesis converts evidence into reusable context.

For each persona, extract:

- Core professional pattern.
- Project taxonomy.
- Idea engine.
- Tacit knowledge.
- Taste and communication model.
- Technical ability model.
- Launch and distribution behavior.
- Safety boundaries.
- Failure modes.
- Evaluation criteria.

The output should be modular. Agents should not need to load a huge monolithic file for every task.

### 4. Evaluation

Every persona needs rubrics.

Rubrics should test:

- Evidence fidelity.
- Non-impersonation.
- Useful abstraction.
- Technical plausibility.
- Safety and ethics.
- Uncertainty handling.
- Style/taste fit without identity mimicry.
- Whether the output is actionable for the user's task.

The Riley package includes both a general rubric and a deeper brain-model rubric:

- `personas/riley-walz/evals/rubric.md`
- `personas/riley-walz/evals/brain-model-rubric.md`

## Framework Concepts

### Context Pack

The compact default context an agent can load for normal work.

### Brain Model

A long-form model of public professional patterns. It should describe observable work style, not private psychology.

### Idea Engine

A structured set of prompts, heuristics, and selection rules for generating projects inspired by the person's public work.

### Technical Intelligence

A model of how the person appears to discover data sources, use tools, compose systems, make trade-offs, and ship artifacts.

For Riley, the technical pattern is:

```text
public-client observation + data-seam detection + state-change inference + cheap collector design + one-screen productization + method framing
```

### Evidence Map

A bridge between research outputs and synthesized claims.

### Safety Boundary

A hard constraint file that prevents the persona system from becoming impersonation, surveillance, or operational abuse.

### Rubric

An evaluation layer that scores generated outputs and keeps the context system honest.

## Contribution Guidelines

Good contributions:

- Add public sources with provenance.
- Improve claim support.
- Add missing safety caveats.
- Improve schema consistency.
- Add better examples.
- Expand rubrics.
- Add a new persona package with clear evidence boundaries.

Bad contributions:

- Private or invasive information.
- Unverified gossip.
- First-person impersonation prompts.
- Instructions for evading platform controls.
- Data harvesting recipes for sensitive sources.
- Claims that cannot be traced back to public evidence.

## New Persona Checklist

Before opening a PR for a new persona, make sure the package includes:

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

For deeper packages, also add:

- `context/brain-model.md`
- `context/idea-engine.md`
- `context/taste-and-voice.md`
- `context/technical-playbook.md`
- `data/quote-bank.json`
- `data/evidence-map.json`
- A `research/` directory with raw research outputs or notes.

## License And Ethics

This project is intended for public-interest research, creative learning, and agent context engineering.

The project should remain evidence-bound and non-impersonating. If a generated output would make a reasonable reader believe it came from the subject, it is out of bounds.

The safe default is:

```text
Study the public pattern. Do not simulate the private person.
```
