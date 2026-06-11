"""peoplereadme CLI (typer)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import httpx
import typer

from . import __version__
from .evidence import append_evidence
from .ingest import ingest_file, ingest_github, ingest_rss, ingest_x_archive
from .initialize import init_persona
from .models import PersonaClass
from .repo import find_repo_root
from .traces import assign_splits, compilability_score, extract_traces, write_traces
from .validate import validate_all, validate_persona_dir

app = typer.Typer(
    name="peoplereadme",
    help="Compile, evaluate, and export evidence-bound persona packages.",
)


@app.callback(invoke_without_command=True)
def _main(
    ctx: typer.Context,
    version: Annotated[bool, typer.Option("--version", help="Show version and exit.")] = False,
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command()
def init(
    persona_id: Annotated[str, typer.Argument(help="Persona id (lowercase kebab-case).")],
    persona_class: Annotated[
        PersonaClass, typer.Option("--class", help="Persona class: self or other.")
    ],
) -> None:
    """Create a schema-valid persona package skeleton and register it in manifest.json."""
    persona_dir = init_persona(persona_id, persona_class)
    typer.echo(f"Created {persona_dir}")
    errors = validate_persona_dir(persona_dir)
    if errors:
        typer.echo("Schema validation FAILED:")
        for err in errors:
            typer.echo(f"  - {err}")
        raise typer.Exit(code=1)
    typer.echo("Schema validation passed.")


@app.command()
def validate(
    persona_id: Annotated[
        str | None, typer.Argument(help="Persona id to validate; omit to validate all.")
    ] = None,
) -> None:
    """Validate persona.json files against schemas/persona.schema.json."""
    root = find_repo_root()
    if persona_id:
        results = {persona_id: validate_persona_dir(root / "personas" / persona_id, root=root)}
    else:
        results = validate_all(root)
    failed = False
    for pid, errors in results.items():
        if errors:
            failed = True
            typer.echo(f"{pid}: FAILED")
            for err in errors:
                typer.echo(f"  - {err}")
        else:
            typer.echo(f"{pid}: ok")
    if not results:
        typer.echo("No persona.json files found; nothing to validate.")
    if failed:
        raise typer.Exit(code=1)


def _persona_dir(persona_id: str) -> Path:
    root = find_repo_root()
    persona_dir = root / "personas" / persona_id
    if not persona_dir.is_dir():
        typer.echo(f"Error: personas/{persona_id}/ does not exist (run init first)", err=True)
        raise typer.Exit(code=1)
    return persona_dir


@app.command()
def ingest(
    persona_id: Annotated[str, typer.Argument(help="Persona id.")],
    source: Annotated[
        list[str],
        typer.Option(
            "--source",
            help="Source spec: x-archive=<zip> | github=<user> | rss=<url> | file=<path>. "
            "Repeatable.",
        ),
    ],
) -> None:
    """Ingest evidence from sources into personas/{id}/evidence/ (incremental)."""
    persona_dir = _persona_dir(persona_id)
    for spec in source:
        kind, _, value = spec.partition("=")
        if not value:
            typer.echo(f"Error: invalid --source spec {spec!r} (expected key=value)", err=True)
            raise typer.Exit(code=2)
        try:
            if kind == "x-archive":
                items, cursor = ingest_x_archive(Path(value))
            elif kind == "github":
                items, cursor = ingest_github(value)
            elif kind == "rss":
                items, cursor = ingest_rss(value)
            elif kind == "file":
                items, cursor = ingest_file(Path(value))
            else:
                typer.echo(f"Error: unknown source kind {kind!r}", err=True)
                raise typer.Exit(code=2)
        except (OSError, ValueError, httpx.HTTPError) as exc:
            typer.echo(f"Error ingesting {spec}: {exc}", err=True)
            raise typer.Exit(code=1) from exc
        source_name = items[0].source if items else kind
        added = append_evidence(persona_dir, source_name, items, cursor=cursor or None)
        typer.echo(f"{kind}: {added} new items ({len(items)} seen)")


@app.command()
def trace(
    persona_id: Annotated[str, typer.Argument(help="Persona id.")],
) -> None:
    """Extract traces from evidence, assign chronological splits, compute compilability."""
    persona_dir = _persona_dir(persona_id)
    traces = assign_splits(extract_traces(persona_dir, persona_id))
    compilability = compilability_score(traces)
    write_traces(persona_dir, traces, compilability)
    counts = {s: sum(1 for t in traces if t.split == s) for s in ("train", "dev", "test")}
    typer.echo(
        f"{len(traces)} traces "
        f"(train={counts['train']} dev={counts['dev']} test={counts['test']})"
    )
    typer.echo(f"Compilability: {compilability.score} ({compilability.band})")


@app.command()
def schema() -> None:
    """Print the persona JSON schema."""
    root = find_repo_root()
    typer.echo(
        json.dumps(
            json.loads((Path(root) / "schemas" / "persona.schema.json").read_text()), indent=2
        )
    )


if __name__ == "__main__":
    app()
