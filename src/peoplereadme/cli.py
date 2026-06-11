"""peoplereadme CLI (typer)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from . import __version__
from .initialize import init_persona
from .models import PersonaClass
from .repo import find_repo_root
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
    try:
        persona_dir = init_persona(persona_id, persona_class)
    except FileExistsError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
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
