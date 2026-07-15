"""Export format writers (PRD 11 / M4): cursor, claude, mcp, prompt.

Each writer renders the same ExportBundle into a target layout under
personas/{id}/exports/{format}/ and returns the files it wrote. `write_exports`
dispatches formats and stamps exports/export.lock.json with content hashes so
re-exports are auditable diffs.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from .. import __version__
from .bundle import ExportBundle, build_bundle

FORMATS = ("cursor", "claude", "mcp", "prompt")


def _header(bundle: ExportBundle) -> str:
    lines = [f"# Persona: {bundle.name} ({bundle.persona_class}-persona)", ""]
    if bundle.non_affiliation:
        lines += [f"> {bundle.non_affiliation}", ""]
    lines += [f"Scope: {bundle.scope}", ""]
    if bundle.disallowed:
        lines += ["Never do:", *[f"- {d}" for d in bundle.disallowed], ""]
    return "\n".join(lines)


def _behavior_rules(bundle: ExportBundle) -> str:
    if bundle.compiled:
        prov = bundle.compiled.provenance
        origin = (
            f"optimized by {prov.get('optimizer', 'compiler')} "
            f"(dev score {prov.get('seed_dev_score')} -> {prov.get('compiled_dev_score')})"
            if prov
            else "from the compiled program"
        )
        return (
            f"## Behavior rules ({origin})\n\n"
            f"### Producing an artifact\n\n{bundle.compiled.draft}\n\n"
            f"### Refining an artifact\n\n{bundle.compiled.refine}\n"
        )
    return ""


def _capabilities_md(bundle: ExportBundle) -> str:
    parts = ["## Capabilities", ""]
    for name, prompt in bundle.capabilities.items():
        parts += [f"### {name}", "", prompt, ""]
    return "\n".join(parts)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def write_cursor(bundle: ExportBundle, out_dir: Path) -> list[Path]:
    body = (
        "---\n"
        f"description: {bundle.name} persona — evidence-bound professional patterns\n"
        "alwaysApply: false\n"
        "---\n\n"
        f"{_header(bundle)}\n"
        f"{_behavior_rules(bundle)}\n"
        f"{_capabilities_md(bundle)}\n"
        f"## Persona brief\n\n{bundle.brief}\n"
    )
    return [_write(out_dir / f"{bundle.persona_id}.mdc", body)]


def write_claude(bundle: ExportBundle, out_dir: Path) -> list[Path]:
    skill = (
        "---\n"
        f"name: persona-{bundle.persona_id}\n"
        f"description: Act with the evidence-bound professional patterns of {bundle.name}. "
        "Use when ideating, reviewing, scope-cutting, or drafting as this persona.\n"
        "---\n\n"
        f"{_header(bundle)}\n"
        f"{_behavior_rules(bundle)}\n"
        f"{_capabilities_md(bundle)}\n"
        "## Persona brief\n\nRead `reference.md` in this skill directory before acting.\n"
    )
    return [
        _write(out_dir / bundle.persona_id / "SKILL.md", skill),
        _write(out_dir / bundle.persona_id / "reference.md", bundle.brief + "\n"),
    ]


def write_prompt(bundle: ExportBundle, out_dir: Path) -> list[Path]:
    system = (
        f"{_header(bundle)}\n"
        f"{_behavior_rules(bundle)}\n"
        f"## Persona brief\n\n{bundle.brief}\n"
    )
    return [
        _write(out_dir / bundle.persona_id / "system-prompt.md", system),
        _write(out_dir / bundle.persona_id / "capabilities.md", _capabilities_md(bundle) + "\n"),
    ]


_MCP_SERVER_TEMPLATE = '''"""Generated MCP server for the {name} persona. Do not edit by hand.

Run: uv run --with mcp python server.py  (stdio transport)
Each tool wraps one exported capability; the persona brief and behavior rules
are embedded so any MCP client gets the full evidence-bound context.
"""

from pathlib import Path

from mcp.server.fastmcp import FastMCP

_DIR = Path(__file__).parent
PERSONA_CONTEXT = (_DIR / "context.md").read_text()

mcp = FastMCP("persona-{persona_id}")

{tools}

if __name__ == "__main__":
    mcp.run()
'''

_MCP_TOOL_TEMPLATE = '''
@mcp.tool()
def {cap}(request: str) -> str:
    """{doc}"""
    return (
        PERSONA_CONTEXT
        + "\\n\\n## Task ({cap})\\n\\n{prompt}\\n\\n## Request\\n\\n"
        + request
    )
'''


def write_mcp(bundle: ExportBundle, out_dir: Path) -> list[Path]:
    server_dir = out_dir / bundle.persona_id
    context = f"{_header(bundle)}\n{_behavior_rules(bundle)}\n## Persona brief\n\n{bundle.brief}\n"
    tools = "".join(
        _MCP_TOOL_TEMPLATE.format(
            cap=cap,
            doc=f"{bundle.name} persona capability: {cap}.",
            prompt=prompt.replace("\\", "\\\\").replace('"', '\\"'),
        )
        for cap, prompt in bundle.capabilities.items()
    )
    server = _MCP_SERVER_TEMPLATE.format(
        name=bundle.name, persona_id=bundle.persona_id, tools=tools
    )
    readme = (
        f"# MCP server: {bundle.name}\n\n"
        "Stdio MCP server exposing this persona's exported capabilities as tools.\n\n"
        "```bash\nuv run --with mcp python server.py\n```\n\n"
        "Register in an MCP client config with command `python` and args `[server.py]`.\n"
    )
    return [
        _write(server_dir / "server.py", server),
        _write(server_dir / "context.md", context),
        _write(server_dir / "README.md", readme),
    ]


_WRITERS = {
    "cursor": write_cursor,
    "claude": write_claude,
    "mcp": write_mcp,
    "prompt": write_prompt,
}


class ExportResult(BaseModel):
    persona: str
    formats: list[str]
    capabilities: list[str]
    compiled: bool
    brief_hash: str
    files: dict[str, str] = Field(default_factory=dict)
    timestamp: str
    peoplereadme_version: str


def write_exports(
    persona_dir: Path, persona_id: str, formats: list[str] | None = None
) -> ExportResult:
    """Render the bundle into each requested format and stamp export.lock.json."""
    formats = list(formats) if formats else list(FORMATS)
    unknown = [f for f in formats if f not in _WRITERS]
    if unknown:
        raise ValueError(
            f"unknown export format(s) {', '.join(sorted(unknown))} "
            f"(supported: {' | '.join(FORMATS)})"
        )
    bundle = build_bundle(persona_dir, persona_id)
    exports_dir = persona_dir / "exports"
    files: dict[str, str] = {}
    for fmt in formats:
        for path in _WRITERS[fmt](bundle, exports_dir / fmt):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            files[str(path.relative_to(persona_dir))] = f"sha256:{digest}"
    result = ExportResult(
        persona=persona_id,
        formats=formats,
        capabilities=list(bundle.capabilities),
        compiled=bundle.compiled is not None,
        brief_hash=bundle.brief_hash,
        files=files,
        timestamp=datetime.now(UTC).isoformat(),
        peoplereadme_version=__version__,
    )
    (exports_dir / "export.lock.json").write_text(result.model_dump_json(indent=2) + "\n")
    return result
