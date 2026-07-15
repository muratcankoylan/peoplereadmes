"""Load and run compiled persona programs; bridge into the M2 harness.

The compiled artifact is state-only JSON (instructions + demos, no secrets);
the persona brief is rebuilt from the package at load time so the program
always runs against the current package content.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..models import Trace
from .data import trace_task
from .program import PersonaProgram, persona_brief


def load_compiled(persona_dir: Path) -> tuple[PersonaProgram, dict]:
    """Load compiled/program.json into a PersonaProgram; returns (program, lock)."""
    compiled_dir = persona_dir / "compiled"
    program_path = compiled_dir / "program.json"
    lock_path = compiled_dir / "compile.lock.json"
    if not program_path.is_file():
        raise FileNotFoundError(
            f"{program_path} not found (run `peoplereadme compile` first)"
        )
    lock = json.loads(lock_path.read_text()) if lock_path.is_file() else {}
    program = PersonaProgram(persona_brief(persona_dir))
    program.load(str(program_path))
    return program, lock


def generate_compiled(program: PersonaProgram, traces: list[Trace]) -> dict[str, str]:
    """Trace-id -> generated artifact, mirroring harness generate_all."""
    out: dict[str, str] = {}
    for t in traces:
        context = t.context.content or "(no context; standalone artifact)"
        prediction = program(task=trace_task(t), context=context)
        out[t.id] = prediction.output or ""
    return out
