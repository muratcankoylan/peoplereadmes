"""FastAPI backend driving the pipeline: ingest -> trace -> compile -> eval -> export.

Every stage runs as a background job (threads) so the UI can poll progress;
all artifacts land in the same personas/{id}/ layout the CLI uses, so the web
UI and the CLI are two fronts over one machine layer.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..evidence import append_evidence, load_evidence, load_sources_lock
from ..harness.lm import LMError, build_lm
from ..harness.run import run_eval
from ..ingest import run_source
from ..initialize import init_persona
from ..models import PersonaClass
from ..repo import find_repo_root
from ..traces import assign_splits, compilability_score, extract_traces, write_traces
from .jobs import Job, registry

DEFAULT_TASK_MODEL = "openai/gpt-5.6-sol"
DEFAULT_REFLECTION_MODEL = "openai/gpt-5.6-terra"

app = FastAPI(title="peoplereadme")


def _root() -> Path:
    return find_repo_root()


def _persona_dir(persona_id: str) -> Path:
    persona_dir = _root() / "personas" / persona_id
    if not persona_dir.is_dir():
        raise HTTPException(404, f"persona {persona_id!r} not found")
    return persona_dir


class CreatePersona(BaseModel):
    persona_id: str
    persona_class: str = "self"


class IngestRequest(BaseModel):
    x_username: str | None = None
    github_username: str | None = None
    rss_urls: list[str] = Field(default_factory=list)
    enrich_name: str | None = None
    enrich_queries: list[str] = Field(default_factory=list)
    model: str = DEFAULT_TASK_MODEL


class CompileRequest(BaseModel):
    model: str = DEFAULT_TASK_MODEL
    reflection_model: str = DEFAULT_REFLECTION_MODEL
    optimizer: str = "gepa"
    auto: str = "light"


class EvalRequest(BaseModel):
    model: str = DEFAULT_TASK_MODEL
    judge_model: str = DEFAULT_REFLECTION_MODEL
    n_pairs: int = 100
    compiled: bool = True
    concurrency: int = 8


class GenerateRequest(BaseModel):
    task: str
    context: str = ""
    model: str = DEFAULT_TASK_MODEL


@app.get("/")
def index() -> FileResponse:
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/api/personas")
def list_personas() -> list[dict]:
    personas_dir = _root() / "personas"
    out = []
    if personas_dir.is_dir():
        for d in sorted(personas_dir.iterdir()):
            if (d / "persona.json").is_file():
                out.append(_persona_summary(d))
    return out


def _persona_summary(persona_dir: Path) -> dict:
    persona = json.loads((persona_dir / "persona.json").read_text())
    traces_path = persona_dir / "traces" / "traces.jsonl"
    splits_path = persona_dir / "traces" / "splits.json"
    splits = json.loads(splits_path.read_text()) if splits_path.is_file() else {}
    lock = load_sources_lock(persona_dir)
    evidence_counts = {
        name: entry.get("item_count", 0) for name, entry in lock.get("sources", {}).items()
    }
    latest_path = persona_dir / "evals" / "fidelity" / "latest.json"
    latest_report = None
    if latest_path.is_file():
        name = json.loads(latest_path.read_text()).get("latest")
        report_path = persona_dir / "evals" / "fidelity" / name if name else None
        if report_path and report_path.is_file():
            latest_report = json.loads(report_path.read_text())
    export_lock_path = persona_dir / "exports" / "export.lock.json"
    return {
        "persona_id": persona_dir.name,
        "name": persona.get("name", persona_dir.name),
        "persona_class": persona.get("class", "other"),
        "evidence": evidence_counts,
        "n_traces": (
            sum(1 for line in traces_path.read_text().splitlines() if line.strip())
            if traces_path.is_file()
            else 0
        ),
        "splits": splits.get("counts", {}),
        "compilability": splits.get("compilability"),
        "compiled": (persona_dir / "compiled" / "program.json").is_file(),
        "compile_lock": _maybe_json(persona_dir / "compiled" / "compile.lock.json"),
        "latest_report": latest_report,
        "exported": export_lock_path.is_file(),
        "active_jobs": registry.active_for(persona_dir.name),
    }


def _maybe_json(path: Path) -> dict | None:
    return json.loads(path.read_text()) if path.is_file() else None


@app.post("/api/personas")
def create_persona(req: CreatePersona) -> dict:
    if req.persona_class not in ("self", "other"):
        raise HTTPException(422, "persona_class must be 'self' or 'other'")
    try:
        persona_dir = init_persona(req.persona_id, PersonaClass(req.persona_class), root=_root())
    except (ValueError, FileExistsError) as exc:
        raise HTTPException(409, str(exc)) from exc
    return _persona_summary(persona_dir)


@app.get("/api/personas/{persona_id}")
def get_persona(persona_id: str) -> dict:
    return _persona_summary(_persona_dir(persona_id))


@app.post("/api/personas/{persona_id}/ingest")
def start_ingest(persona_id: str, req: IngestRequest) -> dict:
    persona_dir = _persona_dir(persona_id)
    specs: list[str] = []
    if req.x_username:
        specs.append(f"x-api={req.x_username.lstrip('@')}")
    if req.github_username:
        specs.append(f"github={req.github_username}")
    specs += [f"rss={u}" for u in req.rss_urls if u.strip()]
    if not specs and not req.enrich_queries:
        raise HTTPException(422, "provide at least one source or enrichment query")

    def work(job: Job) -> dict:
        added_total = 0
        for spec in specs:
            job.log(f"ingesting {spec} ...")
            try:
                items, cursor = run_source(spec)
            except (ValueError, OSError, TimeoutError) as exc:
                job.log(f"WARNING: {spec}: {exc}")
                continue
            source_name = items[0].source if items else spec.partition("=")[0]
            added = append_evidence(
                persona_dir, source_name, items, cursor=cursor or None, spec=spec
            )
            added_total += added
            job.log(f"{spec}: {added} new items ({len(items)} seen)")
        if req.enrich_name and req.enrich_queries:
            from ..ingest.enrich import enrich as run_enrich

            job.log(f"enriching context for {req.enrich_name!r} ...")
            lm = build_lm(req.model, temperature=0.0)
            report = run_enrich(
                persona_dir,
                persona_id,
                req.enrich_name,
                req.enrich_queries,
                lm,
                max_rounds=2,
                max_pages=10,
            )
            added_total += report.total_new_items
            job.log(
                f"enrichment: {report.total_new_items} context items "
                f"({report.stopped_reason})"
            )
        job.log("re-extracting traces ...")
        traces = assign_splits(extract_traces(persona_dir, persona_id))
        compilability = compilability_score(traces)
        write_traces(persona_dir, traces, compilability)
        job.log(
            f"{len(traces)} traces; compilability {compilability.score} "
            f"({compilability.band})"
        )
        return {"added": added_total, "n_traces": len(traces)}

    return registry.start("ingest", persona_id, work).snapshot()


@app.post("/api/personas/{persona_id}/compile")
def start_compile(persona_id: str, req: CompileRequest) -> dict:
    persona_dir = _persona_dir(persona_id)

    def work(job: Job) -> dict:
        import dspy

        from ..compiler import run_compile
        from ..compiler.compile import build_task_lm

        job.log(
            f"compiling with optimizer={req.optimizer} auto={req.auto} "
            f"task={req.model} reflection={req.reflection_model}"
        )
        if req.optimizer == "gepa":
            job.log("GEPA runs hundreds of rollouts; expect ~20-60 min.")
        judge = build_lm(req.reflection_model, temperature=0.0)
        dspy.configure(lm=build_task_lm(req.model))
        result = run_compile(
            persona_dir,
            persona_id,
            judge,
            task_model=req.model,
            reflection_model=req.reflection_model,
            optimizer=req.optimizer,
            auto=req.auto,
        )
        job.log(
            f"done: train={result.n_train} dev={result.n_dev} "
            f"seed={result.seed_dev_score} compiled={result.compiled_dev_score}"
        )
        return {
            "optimizer": result.optimizer,
            "seed_dev_score": result.seed_dev_score,
            "compiled_dev_score": result.compiled_dev_score,
        }

    return registry.start("compile", persona_id, work).snapshot()


@app.post("/api/personas/{persona_id}/eval")
def start_eval(persona_id: str, req: EvalRequest) -> dict:
    persona_dir = _persona_dir(persona_id)

    def work(job: Job) -> dict:
        generator = build_lm(req.model, temperature=0.7, cached=False)
        judge = build_lm(req.judge_model, temperature=0.0)
        compiled_generate = None
        if req.compiled and (persona_dir / "compiled" / "program.json").is_file():
            import dspy

            from ..compiler.compile import build_task_lm
            from ..compiler.runtime import generate_compiled, load_compiled

            job.log("loading compiled program ...")
            program, _lock = load_compiled(persona_dir)
            dspy.configure(lm=build_task_lm(req.model))

            def compiled_generate(pool):
                return generate_compiled(program, pool, concurrency=req.concurrency)

        job.log(
            f"running harness: n_pairs<={req.n_pairs}, generator={req.model}, "
            f"judge={req.judge_model}, concurrency={req.concurrency}"
        )
        report, path = run_eval(
            persona_dir,
            persona_id,
            generator,
            judge,
            n_pairs=req.n_pairs,
            compiled_generate=compiled_generate,
            concurrency=req.concurrency,
        )
        job.log(f"wrote {path.name}")
        return report.model_dump()

    return registry.start("eval", persona_id, work).snapshot()


@app.post("/api/personas/{persona_id}/export")
def start_export(persona_id: str) -> dict:
    persona_dir = _persona_dir(persona_id)

    def work(job: Job) -> dict:
        from ..exports import write_exports

        job.log("rendering exports (cursor, claude, mcp, prompt) ...")
        result = write_exports(persona_dir, persona_id)
        job.log(f"{len(result.files)} files; compiled={result.compiled}")
        return result.model_dump()

    return registry.start("export", persona_id, work).snapshot()


@app.post("/api/personas/{persona_id}/generate")
def generate(persona_id: str, req: GenerateRequest) -> dict:
    """Live playground: run the compiled persona program (or package prompt) once."""
    persona_dir = _persona_dir(persona_id)
    compiled_path = persona_dir / "compiled" / "program.json"
    try:
        if compiled_path.is_file():
            import dspy

            from ..compiler.compile import build_task_lm
            from ..compiler.runtime import load_compiled

            program, _lock = load_compiled(persona_dir)
            dspy.configure(lm=build_task_lm(req.model))
            prediction = program(
                task=req.task,
                context=req.context or "(no context; standalone artifact)",
            )
            return {"output": prediction.output or "", "condition": "compiled"}
        from ..harness.generation import package_as_prompt

        lm = build_lm(req.model, temperature=0.7, cached=False)
        output = lm.complete(package_as_prompt(persona_dir), req.task)
        return {"output": output, "condition": "package"}
    except (LMError, OSError, ValueError) as exc:
        raise HTTPException(502, str(exc)) from exc


@app.get("/api/personas/{persona_id}/traces")
def get_traces(persona_id: str, split: str | None = None, limit: int = 50) -> list[dict]:
    persona_dir = _persona_dir(persona_id)
    path = persona_dir / "traces" / "traces.jsonl"
    if not path.is_file():
        return []
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if split:
        rows = [r for r in rows if r.get("split") == split]
    return rows[-limit:]


@app.get("/api/personas/{persona_id}/evidence")
def get_evidence(persona_id: str, limit: int = 50) -> list[dict]:
    persona_dir = _persona_dir(persona_id)
    items = load_evidence(persona_dir)
    return [i.model_dump() for i in items[-limit:]]


@app.get("/api/personas/{persona_id}/pairs")
def get_pairs(persona_id: str, limit: int = 20) -> list[dict]:
    """Real-vs-generated pairs with judge picks from the latest calibration batch."""
    persona_dir = _persona_dir(persona_id)
    cal_dir = persona_dir / "evals" / "fidelity" / "calibration"
    if not cal_dir.is_dir():
        return []
    batches = sorted(cal_dir.glob("*.jsonl"))
    if not batches:
        return []
    blind = batches[-1]
    answers_path = cal_dir / f"{blind.stem}.answers.json"
    answers = json.loads(answers_path.read_text()) if answers_path.is_file() else {}
    out = []
    for line in blind.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        key = answers.get(row.get("pair_id"), {})
        real_pos = key.get("real")
        row["real"] = row.get(f"candidate_{real_pos.lower()}") if real_pos else None
        row["generated"] = (
            row.get(f"candidate_{'b' if real_pos == 'A' else 'a'}") if real_pos else None
        )
        row["judge_pick"] = key.get("judge_pick")
        row["judge_correct"] = (
            key.get("judge_pick") == real_pos if real_pos and key.get("judge_pick") else None
        )
        out.append(row)
    return out[:limit]


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = registry.get(job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return job.snapshot()
