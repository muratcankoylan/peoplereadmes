"""peoplereadme CLI (typer)."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Annotated
from xml.etree.ElementTree import ParseError

import httpx
import typer

from . import __version__
from .evidence import append_evidence
from .ingest import (
    crawl_firecrawl,
    ingest_file,
    ingest_firecrawl,
    ingest_github,
    ingest_rss,
    ingest_x_api,
    ingest_x_archive,
)
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
            help=(
                "Source spec: x-archive=<zip> | x-api=<user> | github=<user> | "
                "rss=<url> | firecrawl=<url> | firecrawl-crawl=<url> | file=<path>. "
                "Repeatable."
            ),
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
            elif kind == "x-api":
                items, cursor = ingest_x_api(value)
            elif kind == "github":
                items, cursor = ingest_github(value)
            elif kind == "rss":
                items, cursor = ingest_rss(value)
            elif kind == "firecrawl":
                items, cursor = ingest_firecrawl(value)
            elif kind == "firecrawl-crawl":
                items, cursor = crawl_firecrawl(value)
            elif kind == "file":
                items, cursor = ingest_file(Path(value))
            else:
                typer.echo(f"Error: unknown source kind {kind!r}", err=True)
                raise typer.Exit(code=2)
        except (
            OSError,
            ValueError,
            KeyError,
            zipfile.BadZipFile,
            ParseError,
            TimeoutError,
            httpx.HTTPError,
        ) as exc:
            typer.echo(f"Error ingesting {spec}: {exc}", err=True)
            raise typer.Exit(code=1) from exc
        source_name = items[0].source if items else kind
        added = append_evidence(persona_dir, source_name, items, cursor=cursor or None)
        typer.echo(f"{kind}: {added} new items ({len(items)} seen)")


@app.command()
def enrich(
    persona_id: Annotated[str, typer.Argument(help="Persona id.")],
    name: Annotated[str, typer.Option("--name", help="Person's public name for research.")],
    query: Annotated[
        list[str],
        typer.Option("--query", help="Seed discovery query. Repeatable."),
    ],
    model: Annotated[
        str | None,
        typer.Option("--model", help="LM slug for lead extraction; omit for single pass."),
    ] = None,
    max_rounds: Annotated[
        int, typer.Option("--max-rounds", help="Max discover->scrape->extract rounds.")
    ] = 2,
    max_pages: Annotated[
        int, typer.Option("--max-pages", help="Total page-scrape budget.")
    ] = 10,
) -> None:
    """Recursive context enrichment: discover -> scrape -> extract leads -> go deeper."""
    from .ingest.enrich import enrich as run_enrich

    persona_dir = _persona_dir(persona_id)
    lm = None
    if model:
        from .harness.lm import build_lm

        lm = build_lm(model, temperature=0.0)
    try:
        report = run_enrich(
            persona_dir,
            persona_id,
            name,
            query,
            lm,
            max_rounds=max_rounds,
            max_pages=max_pages,
        )
    except (OSError, ValueError, TimeoutError, httpx.HTTPError) as exc:
        typer.echo(f"Error enriching {persona_id}: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    for rnd in report.rounds:
        typer.echo(
            f"round {rnd.round}: {len(rnd.discovered_urls)} discovered, "
            f"{len(rnd.scraped_urls)} scraped, {rnd.new_items} new items"
        )
    typer.echo(f"total new items: {report.total_new_items} ({report.stopped_reason})")
    typer.echo("Audit log: evidence/enrichment.log.json")


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


DEFAULT_TASK_MODEL = "openai/gpt-5.6-sol"
DEFAULT_REFLECTION_MODEL = "openai/gpt-5.6-terra"


@app.command("compile")
def compile_cmd(
    persona_id: Annotated[str, typer.Argument(help="Persona id.")],
    model: Annotated[
        str, typer.Option("--model", help="Task model slug (litellm).")
    ] = DEFAULT_TASK_MODEL,
    reflection_model: Annotated[
        str,
        typer.Option("--reflection-model", help="GEPA reflection model slug."),
    ] = DEFAULT_REFLECTION_MODEL,
    judge_model: Annotated[
        str | None,
        typer.Option("--judge-model", help="Metric judge slug; defaults to --reflection-model."),
    ] = None,
    optimizer: Annotated[
        str, typer.Option("--optimizer", help="none | bootstrap | gepa.")
    ] = "gepa",
    auto: Annotated[
        str, typer.Option("--auto", help="GEPA budget: light | medium | heavy.")
    ] = "light",
    seed: Annotated[int, typer.Option("--seed", help="Optimizer seed.")] = 0,
    max_train: Annotated[
        int | None, typer.Option("--max-train", help="Cap train examples.")
    ] = None,
    max_dev: Annotated[
        int | None, typer.Option("--max-dev", help="Cap dev examples.")
    ] = None,
) -> None:
    """Compile the persona into an optimized DSPy program (M3). Test split untouched."""
    import dspy

    from .compiler import run_compile
    from .compiler.compile import build_task_lm
    from .harness.lm import LMError, build_lm

    persona_dir = _persona_dir(persona_id)
    judge = build_lm(judge_model or reflection_model, temperature=0.0)
    dspy.configure(lm=build_task_lm(model))
    try:
        result = run_compile(
            persona_dir,
            persona_id,
            judge,
            task_model=model,
            reflection_model=reflection_model,
            optimizer=optimizer,
            auto=auto,
            seed=seed,
            max_train=max_train,
            max_dev=max_dev,
        )
    except (OSError, ValueError, LMError) as exc:
        typer.echo(f"Error compiling {persona_id}: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"optimizer: {result.optimizer}  train={result.n_train} dev={result.n_dev}")
    if result.seed_dev_score is not None:
        typer.echo(
            f"dev score: seed={result.seed_dev_score} compiled={result.compiled_dev_score}"
        )
    typer.echo(f"Wrote {persona_dir / result.program_path} and compiled/compile.lock.json")


@app.command("eval")
def eval_cmd(
    persona_id: Annotated[str, typer.Argument(help="Persona id.")],
    model: Annotated[str, typer.Option("--model", help="Generator model slug (litellm).")],
    judge_model: Annotated[
        str | None,
        typer.Option("--judge-model", help="Judge model slug; defaults to --model."),
    ] = None,
    n_pairs: Annotated[
        int, typer.Option("--n-pairs", help="Max pairwise comparisons (PRD: >=100).")
    ] = 100,
    seed: Annotated[int, typer.Option("--seed", help="Sampling/bootstrap seed.")] = 0,
    skip_baseline: Annotated[
        bool, typer.Option("--skip-baseline", help="Skip the raw-model baseline run.")
    ] = False,
    compiled: Annotated[
        bool,
        typer.Option("--compiled", help="Evaluate the compiled program (M3) as headline."),
    ] = False,
) -> None:
    """Run the fidelity harness: pairwise judge, rubric dimensions, baselines."""
    from .harness.lm import LMError, build_lm
    from .harness.run import run_eval

    persona_dir = _persona_dir(persona_id)
    generator = build_lm(model, temperature=0.7, cached=False)
    judge = build_lm(judge_model or model, temperature=0.0)
    compiled_generate = None
    if compiled:
        import dspy

        from .compiler.compile import build_task_lm
        from .compiler.runtime import generate_compiled, load_compiled

        try:
            program, _lock = load_compiled(persona_dir)
        except (OSError, ValueError) as exc:
            typer.echo(f"Error loading compiled program: {exc}", err=True)
            raise typer.Exit(code=1) from exc
        dspy.configure(lm=build_task_lm(model))

        def compiled_generate(pool):
            return generate_compiled(program, pool)

    try:
        report, path = run_eval(
            persona_dir,
            persona_id,
            generator,
            judge,
            n_pairs=n_pairs,
            seed=seed,
            skip_baseline=skip_baseline,
            compiled_generate=compiled_generate,
        )
    except (OSError, ValueError, LMError, httpx.HTTPError) as exc:
        typer.echo(f"Error running eval: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    ind = report.indistinguishability
    typer.echo(f"n_pairs: {report.n_test}")
    typer.echo(
        f"judge_accuracy: {ind.judge_accuracy}  "
        f"indistinguishability: {ind.score} (ci95 {ind.ci95[0]}-{ind.ci95[1]})"
    )
    for dim, value in report.dimensions.items():
        typer.echo(f"  {dim}: {value}")
    for name, delta in report.baseline_delta.items():
        typer.echo(f"delta {name}: {delta}")
    if report.n_test < 100:
        typer.echo("WARNING: n_pairs < 100 — not a valid report card (PRD 9.5).", err=True)
    typer.echo(f"Wrote {path}")
    typer.echo(
        "Calibration batch exported to evals/fidelity/calibration/ — rate >=50 pairs "
        "and run `peoplereadme calibrate` to stamp kappa."
    )


@app.command()
def calibrate(
    persona_id: Annotated[str, typer.Argument(help="Persona id.")],
    batch: Annotated[str, typer.Option("--batch", help="Batch name (fidelity date stamp).")],
    ratings: Annotated[
        Path, typer.Option("--ratings", help="JSONL with human_pick filled in.")
    ],
) -> None:
    """Import human ratings, compute judge-vs-human Cohen's kappa, stamp fidelity.json."""
    from .harness.calibration import KAPPA_HARD_FLOOR, import_calibration

    persona_dir = _persona_dir(persona_id)
    try:
        result = import_calibration(persona_dir, batch, ratings)
    except (OSError, ValueError) as exc:
        typer.echo(f"Error importing calibration: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(
        f"kappa: {result.kappa} over {result.n_pairs} pairs "
        f"(human accuracy {result.human_accuracy})"
    )
    fidelity_path = persona_dir / "evals" / "fidelity" / f"{batch}.json"
    if fidelity_path.is_file():
        data = json.loads(fidelity_path.read_text())
        data["judge"]["human_agreement_kappa"] = result.kappa
        data["judge"]["n_calibration_pairs"] = result.n_pairs
        fidelity_path.write_text(json.dumps(data, indent=2) + "\n")
        typer.echo(f"Stamped {fidelity_path}")
    if not result.valid:
        typer.echo(
            f"INVALID report card: kappa < {KAPPA_HARD_FLOOR} or fewer than 50 rated "
            "pairs — revise the rubric or judge (PRD 9.5).",
            err=True,
        )
        raise typer.Exit(code=1)


@app.command()
def rubric(
    persona_id: Annotated[str, typer.Argument(help="Persona id.")],
) -> None:
    """Write the codified rubric (evals/rubrics/v1.json) for a persona."""
    from .harness.rubric import write_default_rubric

    persona_dir = _persona_dir(persona_id)
    path = write_default_rubric(persona_dir)
    typer.echo(f"Wrote {path}")


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
