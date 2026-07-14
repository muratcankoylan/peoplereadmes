"""Recursive enrichment: discover -> scrape -> extract -> go deeper.

Bounded context expansion around a persona. Each round: run discovery queries,
scrape novel URLs with Firecrawl into press-tier evidence, then use an LM to
extract new entities/queries/links from what was scraped to seed the next
round. Stops on max_rounds, max_pages budget, or when a round yields nothing
novel. Every round is recorded in evidence/enrichment.log.json for audit.

Press-tier evidence enriches context only; it never becomes behavior traces
(see traces.extract_traces).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

from ..evidence import append_evidence, evidence_dir, load_evidence
from .firecrawl import ingest_firecrawl
from .research import discover_sources

SKIP_DOMAINS = {
    "x.com",
    "twitter.com",
    "github.com",
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "youtube.com",
    "youtu.be",
}
SKIP_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg", ".gif", ".zip", ".mp4", ".mp3")

EXTRACT_SYSTEM = (
    "You extract research leads from scraped web content about a person. "
    "Given the person's name and page excerpts, return strict JSON: "
    '{"queries": [...], "urls": [...]}. '
    "queries: up to {max_queries} new web-search queries that would surface more "
    "public professional context about this person (projects, launches, talks, "
    "writing, collaborations mentioned in the text). "
    "urls: up to {max_urls} concrete URLs mentioned in the text worth scraping. "
    "Only public professional material; never private, personal, or contact data."
)


class EnrichmentRound(BaseModel):
    round: int
    queries: list[str]
    discovered_urls: list[str]
    scraped_urls: list[str]
    skipped_urls: list[str]
    failed_urls: list[str]
    new_items: int


class EnrichmentReport(BaseModel):
    persona: str
    name: str
    started_at: str
    finished_at: str = ""
    max_rounds: int
    max_pages: int
    rounds: list[EnrichmentRound] = Field(default_factory=list)
    total_new_items: int = 0
    stopped_reason: str = ""


def _norm_url(url: str) -> str:
    return url.rstrip("/").split("#", 1)[0]


def _skippable(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return True
    host = (parsed.hostname or "").lower()
    if any(host == d or host.endswith(f".{d}") for d in SKIP_DOMAINS):
        return True
    return parsed.path.lower().endswith(SKIP_EXTENSIONS)


def _extract_leads(
    lm, name: str, contents: list[str], max_queries: int = 5, max_urls: int = 5
) -> tuple[list[str], list[str]]:
    from ..harness.lm import extract_json

    excerpts = "\n\n---\n\n".join(c[:4000] for c in contents if c.strip())[:24000]
    if not excerpts:
        return [], []
    system = EXTRACT_SYSTEM.replace("{max_queries}", str(max_queries)).replace(
        "{max_urls}", str(max_urls)
    )
    user = f"Person: {name}\n\nScraped content:\n{excerpts}"
    try:
        data = extract_json(lm.complete(system, user))
    except ValueError:
        return [], []
    raw_queries = data.get("queries", [])
    raw_urls = data.get("urls", [])
    if not isinstance(raw_queries, list):
        raw_queries = []
    if not isinstance(raw_urls, list):
        raw_urls = []
    queries = [q for q in raw_queries if isinstance(q, str) and q.strip()]
    urls = [u for u in raw_urls if isinstance(u, str) and u.strip()]
    return queries[:max_queries], urls[:max_urls]


def _log_path(persona_dir: Path) -> Path:
    return evidence_dir(persona_dir) / "enrichment.log.json"


def _write_log(persona_dir: Path, report: EnrichmentReport) -> Path:
    path = _log_path(persona_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    history: list[dict] = []
    if path.is_file():
        history = json.loads(path.read_text())
    history.append(report.model_dump())
    path.write_text(json.dumps(history, indent=2) + "\n")
    return path


def enrich(
    persona_dir: Path,
    persona_id: str,
    name: str,
    seed_queries: list[str],
    lm=None,
    *,
    max_rounds: int = 2,
    max_pages: int = 10,
    per_query_limit: int = 8,
    client: httpx.Client | None = None,
) -> EnrichmentReport:
    """Run the bounded discover->scrape->extract loop. Returns the audit report."""
    report = EnrichmentReport(
        persona=persona_id,
        name=name,
        started_at=datetime.now(UTC).isoformat(),
        max_rounds=max_rounds,
        max_pages=max_pages,
    )
    seen = {_norm_url(item.url) for item in load_evidence(persona_dir)}
    pages_left = max_pages
    queries = [q for q in seed_queries if q.strip()]
    pending_urls: list[str] = []

    for round_no in range(max_rounds):
        if pages_left <= 0:
            report.stopped_reason = "page budget exhausted"
            break
        discovered: list[str] = list(pending_urls)
        pending_urls = []
        for query in queries:
            discovered.extend(
                discover_sources(query, client=client, limit=per_query_limit)
            )

        scraped: list[str] = []
        skipped: list[str] = []
        failed: list[str] = []
        new_items = 0
        contents: list[str] = []
        for url in discovered:
            norm = _norm_url(url)
            if norm in seen or _skippable(url):
                skipped.append(url)
                continue
            seen.add(norm)
            if pages_left <= 0:
                skipped.append(url)
                continue
            try:
                items, cursor = ingest_firecrawl(url, client=client, tier="press")
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                failed.append(f"{url} ({exc})")
                continue
            pages_left -= 1
            scraped.append(url)
            added = append_evidence(persona_dir, "firecrawl", items, cursor=cursor or None)
            new_items += added
            if added:
                contents.extend(item.content for item in items)

        report.rounds.append(
            EnrichmentRound(
                round=round_no,
                queries=queries,
                discovered_urls=discovered,
                scraped_urls=scraped,
                skipped_urls=skipped,
                failed_urls=failed,
                new_items=new_items,
            )
        )
        report.total_new_items += new_items

        if new_items == 0:
            report.stopped_reason = "no novel content this round"
            break
        if round_no + 1 >= max_rounds:
            report.stopped_reason = "max rounds reached"
            break
        if lm is None:
            report.stopped_reason = "no LM for lead extraction"
            break
        queries, pending_urls = _extract_leads(lm, name, contents)
        if not queries and not pending_urls:
            report.stopped_reason = "no new leads extracted"
            break

    if not report.stopped_reason:
        report.stopped_reason = "max rounds reached"
    report.finished_at = datetime.now(UTC).isoformat()
    _write_log(persona_dir, report)
    return report
