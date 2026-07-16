"""Export tests: bundle gating, format writers, lock stamping, CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from peoplereadme.exports import build_bundle, write_exports
from peoplereadme.initialize import NON_AFFILIATION_HEADER, init_persona
from peoplereadme.models import PersonaClass


def _persona(tmp_repo: Path, persona_class: PersonaClass = PersonaClass.SELF) -> Path:
    persona_dir = init_persona("p", persona_class, root=tmp_repo)
    (persona_dir / "context" / "context-pack.md").write_text(
        "# Context\n\nships tiny scrapers, launches on fridays.\n"
    )
    return persona_dir


def _add_compiled(persona_dir: Path) -> None:
    state = {
        "draft": {"signature": {"instructions": "OPTIMIZED DRAFT RULES"}},
        "refine": {"signature": {"instructions": "OPTIMIZED REFINE RULES"}},
    }
    (persona_dir / "compiled" / "program.json").write_text(json.dumps(state))
    (persona_dir / "compiled" / "compile.lock.json").write_text(
        json.dumps(
            {
                "optimizer": "gepa",
                "task_model": "openai/gpt-5.6-sol",
                "seed_dev_score": 0.385,
                "compiled_dev_score": 0.625,
            }
        )
    )


def test_bundle_self_persona_includes_voice(tmp_repo):
    persona_dir = _persona(tmp_repo)
    bundle = build_bundle(persona_dir, "p")
    assert "voice" in bundle.capabilities
    assert bundle.non_affiliation is None
    assert bundle.brief_hash.startswith("sha256:")


def test_bundle_other_persona_excludes_voice_and_carries_header(tmp_repo):
    persona_dir = _persona(tmp_repo, PersonaClass.OTHER)
    persona = json.loads((persona_dir / "persona.json").read_text())
    persona["allowed_exports"].append("voice")  # even if manually added
    (persona_dir / "persona.json").write_text(json.dumps(persona))
    bundle = build_bundle(persona_dir, "p")
    assert "voice" not in bundle.capabilities
    assert bundle.non_affiliation == NON_AFFILIATION_HEADER


def test_bundle_no_capabilities_errors(tmp_repo):
    persona_dir = _persona(tmp_repo)
    persona = json.loads((persona_dir / "persona.json").read_text())
    persona["allowed_exports"] = []
    (persona_dir / "persona.json").write_text(json.dumps(persona))
    with pytest.raises(ValueError, match="allowed_exports"):
        build_bundle(persona_dir, "p")


def test_bundle_picks_up_compiled_instructions(tmp_repo):
    persona_dir = _persona(tmp_repo)
    _add_compiled(persona_dir)
    bundle = build_bundle(persona_dir, "p")
    assert bundle.compiled is not None
    assert bundle.compiled.draft == "OPTIMIZED DRAFT RULES"
    assert bundle.compiled.provenance["optimizer"] == "gepa"


def test_write_exports_all_formats_and_lock(tmp_repo):
    persona_dir = _persona(tmp_repo)
    _add_compiled(persona_dir)
    result = write_exports(persona_dir, "p")
    assert result.formats == ["cursor", "claude", "mcp", "prompt"]
    assert result.compiled is True
    expected = {
        "exports/cursor/p.mdc",
        "exports/claude/p/SKILL.md",
        "exports/claude/p/reference.md",
        "exports/mcp/p/server.py",
        "exports/mcp/p/context.md",
        "exports/mcp/p/README.md",
        "exports/prompt/p/system-prompt.md",
        "exports/prompt/p/capabilities.md",
    }
    assert set(result.files) == expected
    for rel, digest in result.files.items():
        assert (persona_dir / rel).is_file()
        assert digest.startswith("sha256:")
    lock = json.loads((persona_dir / "exports" / "export.lock.json").read_text())
    assert lock["capabilities"] == result.capabilities
    cursor = (persona_dir / "exports" / "cursor" / "p.mdc").read_text()
    assert "OPTIMIZED DRAFT RULES" in cursor
    assert "ships tiny scrapers" in cursor


def test_other_persona_exports_stamp_header_everywhere(tmp_repo):
    persona_dir = _persona(tmp_repo, PersonaClass.OTHER)
    result = write_exports(persona_dir, "p")
    for rel in result.files:
        if rel.endswith(("README.md", "capabilities.md", "server.py")):
            continue
        assert NON_AFFILIATION_HEADER in (persona_dir / rel).read_text(), rel


def test_mcp_server_is_valid_python_with_tools(tmp_repo):
    persona_dir = _persona(tmp_repo)
    write_exports(persona_dir, "p", formats=["mcp"])
    source = (persona_dir / "exports" / "mcp" / "p" / "server.py").read_text()
    compile(source, "server.py", "exec")
    for cap in ("idea_engine", "taste_filter", "scope_cut", "voice"):
        assert f"def {cap}(" in source


def test_unknown_format_errors(tmp_repo):
    persona_dir = _persona(tmp_repo)
    with pytest.raises(ValueError, match="unknown export format"):
        write_exports(persona_dir, "p", formats=["cursor", "bogus"])


def test_export_cli(tmp_repo, monkeypatch):
    from typer.testing import CliRunner

    from peoplereadme.cli import app

    _persona(tmp_repo)
    monkeypatch.chdir(tmp_repo)
    runner = CliRunner()
    result = runner.invoke(app, ["export", "p", "--format", "prompt"])
    assert result.exit_code == 0
    assert "formats: prompt" in result.output
    assert "no (package-only)" in result.output

    result = runner.invoke(app, ["export", "p", "--format", "bogus"])
    assert result.exit_code == 1
    assert "unknown export format" in result.output
