"""Candidate generation for the harness.

Two v1 conditions (PRD 9.5 baselines; compiled personas arrive in M3):
- raw: no persona context at all.
- package: package-as-prompt — the package's own load order stuffed into the
  system prompt, no compilation.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..models import Trace

# Character budget for package-as-prompt; large-context models handle this fine
# but we keep it bounded so judge/generation costs stay predictable.
PACKAGE_PROMPT_CHAR_BUDGET = 60_000

_PACKAGE_FILE_ORDER = [
    "README.md",
    "context/context-pack.md",
    "context/brain-model.md",
    "context/idea-engine.md",
    "context/taste-and-voice.md",
    "context/tacit-knowledge.md",
    "context/project-patterns.md",
    "context/technical-playbook.md",
    "prompts/system-prompt.md",
    "context/safety-boundaries.md",
    "data/heuristics.json",
    "data/quote-bank.json",
]

_KIND_TASK = {
    "post": "Write the post this person would publish right now.",
    "thread": "Write the next post this person would add to the thread below.",
    "reply": "Write the reply this person would post.",
    "commit": "Write the commit message this person would write for this change.",
    "pr_review": "Write the code review comment this person would leave.",
    "launch": "Write the launch post this person would publish for this artifact.",
    "article": "Write the article or blog post this person would publish.",
    "decision": "State the decision this person would make and their rationale.",
}


def package_as_prompt(persona_dir: Path) -> str:
    """Concatenate the package's files (README load order) into one system prompt."""
    parts: list[str] = []
    used = 0
    for rel in _PACKAGE_FILE_ORDER:
        path = persona_dir / rel
        if not path.is_file():
            continue
        text = path.read_text()
        if rel.endswith(".json"):
            try:
                text = json.dumps(json.loads(text), indent=2)
            except ValueError:
                pass
        block = f"\n\n===== {rel} =====\n{text}"
        if used + len(block) > PACKAGE_PROMPT_CHAR_BUDGET:
            block = block[: PACKAGE_PROMPT_CHAR_BUDGET - used]
        parts.append(block)
        used += len(block)
        if used >= PACKAGE_PROMPT_CHAR_BUDGET:
            break
    header = (
        "You are simulating the professional output of the person described in the "
        "persona package below. Produce outputs exactly as this person would write "
        "them: their length, formatting, diction, and judgment. Do not explain "
        "yourself, do not add meta-commentary, output only the artifact."
    )
    return header + "".join(parts)


RAW_SYSTEM_PROMPT = (
    "Produce the requested artifact directly. Output only the artifact itself: "
    "no preamble, no meta-commentary."
)


def behavior_prompt(trace: Trace) -> str:
    task = _KIND_TASK.get(trace.kind, "Write the output this person would produce.")
    lines = [task]
    if trace.context.content:
        lines.append(f"\nContext ({trace.context.type}):\n{trace.context.content}")
    else:
        lines.append("\nThere is no additional context; this is a standalone artifact.")
    lines.append(
        "\nMatch realistic length for this artifact type. Output only the artifact text."
    )
    return "\n".join(lines)
