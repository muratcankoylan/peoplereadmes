"""Ingestion tests: X archive zip, GitHub (mock transport), RSS/Atom, file drops."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import httpx

from peoplereadme.evidence import append_evidence, load_evidence, load_sources_lock
from peoplereadme.ingest import (
    discover_sources,
    ingest_file,
    ingest_firecrawl,
    ingest_github,
    ingest_rss,
    ingest_x_api,
    ingest_x_archive,
)
from peoplereadme.ingest.rss import parse_feed

TWEETS = [
    {
        "tweet": {
            "id_str": "1",
            "created_at": "Mon Jan 05 10:00:00 +0000 2026",
            "full_text": "shipping a thing today",
        }
    },
    {
        "tweet": {
            "id_str": "2",
            "created_at": "Mon Jan 05 11:00:00 +0000 2026",
            "full_text": "it uses public data",
            "in_reply_to_status_id_str": "1",
            "in_reply_to_screen_name": "testuser",
        }
    },
    {
        "tweet": {
            "id_str": "3",
            "created_at": "Tue Jan 06 09:00:00 +0000 2026",
            "full_text": "@someone nice idea",
            "in_reply_to_status_id_str": "999",
            "in_reply_to_screen_name": "someone",
        }
    },
]


def make_archive(path: Path) -> Path:
    zip_path = path / "archive.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(
            "data/account.js",
            "window.YTD.account.part0 = "
            + json.dumps([{"account": {"username": "testuser"}}]),
        )
        zf.writestr("data/tweets.js", "window.YTD.tweets.part0 = " + json.dumps(TWEETS))
    return zip_path


def test_x_archive_ingest(tmp_path: Path):
    items, cursor = ingest_x_archive(make_archive(tmp_path))
    assert len(items) == 3
    assert items[0].kind == "post"
    assert items[1].kind == "reply"
    assert items[0].url == "https://x.com/testuser/status/1"
    assert items[0].timestamp == "2026-01-05T10:00:00+00:00"
    assert cursor == items[-1].timestamp
    assert all(i.hash == "" for i in items)  # hashed on append


def test_append_evidence_dedup_and_lock(tmp_path: Path):
    items, cursor = ingest_x_archive(make_archive(tmp_path))
    persona_dir = tmp_path / "personas" / "p"
    assert append_evidence(persona_dir, "x-archive", items, cursor=cursor) == 3
    # Re-running is incremental: nothing new is appended.
    assert append_evidence(persona_dir, "x-archive", items, cursor=cursor) == 0
    stored = load_evidence(persona_dir)
    assert len(stored) == 3
    assert all(i.hash.startswith("sha256:") for i in stored)
    lock = load_sources_lock(persona_dir)["sources"]["x-archive"]
    assert lock["item_count"] == 3
    assert lock["last_cursor"] == cursor
    assert lock["merkle_root"].startswith("sha256:")


def test_github_ingest_mock():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/users/testuser/repos":
            return httpx.Response(
                200,
                json=[
                    {
                        "name": "tool",
                        "full_name": "testuser/tool",
                        "html_url": "https://github.com/testuser/tool",
                        "created_at": "2026-01-01T00:00:00Z",
                        "description": "a tool",
                        "fork": False,
                        "language": "Python",
                    }
                ],
            )
        if request.url.path == "/repos/testuser/tool/commits":
            return httpx.Response(
                200,
                json=[
                    {
                        "sha": "abc",
                        "html_url": "https://github.com/testuser/tool/commit/abc",
                        "commit": {
                            "message": "add scraper",
                            "author": {"date": "2026-01-02T00:00:00Z"},
                        },
                    }
                ],
            )
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    items, cursor = ingest_github("testuser", client=client)
    kinds = {i.kind for i in items}
    assert kinds == {"project", "commit"}
    assert cursor == "2026-01-02T00:00:00Z"


def test_x_api_ingest_mock():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/2/users/by/username/testuser":
            return httpx.Response(200, json={"data": {"id": "42", "username": "testuser"}})
        if request.url.path == "/2/users/42/tweets":
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "1",
                            "created_at": "2026-01-05T10:00:00Z",
                            "text": "shipping a thing today",
                            "author_id": "42",
                        },
                        {
                            "id": "2",
                            "created_at": "2026-01-05T11:00:00Z",
                            "text": "it uses public data",
                            "author_id": "42",
                            "in_reply_to_user_id": "42",
                            "referenced_tweets": [{"type": "replied_to", "id": "1"}],
                        },
                    ],
                    "includes": {
                        "users": [{"id": "42", "username": "testuser"}],
                        "tweets": [
                            {"id": "1", "author_id": "42"},
                            {"id": "2", "author_id": "42"},
                        ],
                    },
                },
            )
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    items, cursor = ingest_x_api("testuser", client=client)
    assert [i.kind for i in items] == ["post", "reply"]
    assert items[0].source == "x-api"
    assert items[0].url == "https://x.com/testuser/status/1"
    assert items[1].extra == {
        "tweet_id": "2",
        "in_reply_to_status_id": "1",
        "in_reply_to_screen_name": "testuser",
    }
    assert cursor == "2026-01-05T11:00:00Z"


def test_firecrawl_ingest_mock():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/scrape"
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": {
                    "markdown": "# Hello\n\nWorld",
                    "metadata": {
                        "title": "Hello",
                        "sourceURL": "https://example.com/post",
                        "publishedDate": "2026-01-07T00:00:00Z",
                    },
                },
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    items, cursor = ingest_firecrawl("https://example.com/post", client=client)
    assert len(items) == 1
    assert items[0].source == "firecrawl"
    assert items[0].tier == "press"
    assert items[0].content == "# Hello\n\nWorld"
    assert items[0].url == "https://example.com/post"
    assert cursor == "2026-01-07T00:00:00Z"


RSS_XML = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>Blog</title>
<item><title>Post one</title><link>https://blog.example/one</link>
<pubDate>Mon, 05 Jan 2026 10:00:00 GMT</pubDate><description>Body</description></item>
</channel></rss>"""

ATOM_XML = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Blog</title>
<entry><title>Atom post</title><link href="https://blog.example/atom"/>
<published>2026-01-06T10:00:00Z</published><summary>Atom body</summary></entry>
</feed>"""


def test_rss_and_atom_parse():
    rss_items = parse_feed(RSS_XML)
    assert len(rss_items) == 1
    assert rss_items[0].kind == "article"
    assert rss_items[0].url == "https://blog.example/one"
    assert rss_items[0].timestamp == "2026-01-05T10:00:00+00:00"
    atom_items = parse_feed(ATOM_XML)
    assert atom_items[0].url == "https://blog.example/atom"
    assert "Atom body" in atom_items[0].content


def test_rss_ingest_mock():
    client = httpx.Client(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, text=RSS_XML))
    )
    items, cursor = ingest_rss("https://blog.example/feed.xml", client=client)
    assert len(items) == 1
    assert cursor == items[0].timestamp


def test_research_discover_parallel_mock(monkeypatch):
    monkeypatch.setenv("PARALLEL_API_KEY", "parallel-key")
    monkeypatch.delenv("EXA_API_KEY", raising=False)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/search"
        return httpx.Response(
            200,
            json={
                "results": [
                    {"url": "https://example.com/a"},
                    {"url": "https://example.com/b"},
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    urls = discover_sources("topic", client=client, limit=2)
    assert urls == ["https://example.com/a", "https://example.com/b"]


def test_research_discover_exa_mock(monkeypatch):
    monkeypatch.delenv("PARALLEL_API_KEY", raising=False)
    monkeypatch.setenv("EXA_API_KEY", "exa-key")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/search"
        return httpx.Response(
            200,
            json={
                "results": [
                    {"url": "https://example.com/c"},
                    {"url": "https://example.com/d"},
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    urls = discover_sources("topic", client=client, limit=1)
    assert urls == ["https://example.com/c"]


def test_iso_naive_dates_coerced_to_utc():
    from peoplereadme.ingest.rss import _iso

    assert _iso("2026-01-05T10:00:00") == "2026-01-05T10:00:00+00:00"
    assert _iso("2026-01-05T10:00:00Z") == "2026-01-05T10:00:00+00:00"


def test_github_own_client_closed(monkeypatch):
    closed = []

    class TrackingClient(httpx.Client):
        def close(self):
            closed.append(True)
            super().close()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    monkeypatch.setattr(
        "peoplereadme.ingest.github._client",
        lambda c: c or TrackingClient(transport=httpx.MockTransport(handler)),
    )
    ingest_github("testuser")
    assert closed


def test_file_ingest(tmp_path: Path):
    drop = tmp_path / "talk.md"
    drop.write_text("# Talk transcript\nhello")
    items, cursor = ingest_file(drop)
    assert len(items) == 1
    assert items[0].source == "file"
    assert items[0].content.startswith("# Talk transcript")
    assert cursor == items[0].timestamp


def test_press_tier_is_skipped_and_x_api_threads(tmp_path: Path):
    persona_dir = tmp_path / "personas" / "p"

    def x_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/2/users/by/username/testuser":
            return httpx.Response(200, json={"data": {"id": "42", "username": "testuser"}})
        if request.url.path == "/2/users/42/tweets":
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "1",
                            "created_at": "2026-01-05T10:00:00Z",
                            "text": "shipping a thing today",
                            "author_id": "42",
                        },
                        {
                            "id": "2",
                            "created_at": "2026-01-05T11:00:00Z",
                            "text": "it uses public data",
                            "author_id": "42",
                            "in_reply_to_user_id": "42",
                            "referenced_tweets": [{"type": "replied_to", "id": "1"}],
                        },
                    ],
                    "includes": {
                        "users": [{"id": "42", "username": "testuser"}],
                        "tweets": [
                            {"id": "1", "author_id": "42"},
                            {"id": "2", "author_id": "42"},
                        ],
                    },
                },
            )
        return httpx.Response(404)

    def firecrawl_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/scrape"
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": {
                    "markdown": "press article",
                    "metadata": {
                        "title": "Press",
                        "sourceURL": "https://press.example/article",
                        "publishedDate": "2026-01-04T00:00:00Z",
                    },
                },
            },
        )

    x_client = httpx.Client(transport=httpx.MockTransport(x_handler))
    firecrawl_client = httpx.Client(transport=httpx.MockTransport(firecrawl_handler))
    x_items, _ = ingest_x_api("testuser", client=x_client)
    press_items, _ = ingest_firecrawl("https://press.example/article", client=firecrawl_client)
    append_evidence(persona_dir, "x-api", x_items)
    append_evidence(persona_dir, "firecrawl", press_items)

    from peoplereadme.traces import extract_traces

    traces = extract_traces(persona_dir, "p")
    assert len(traces) == 2
    assert [t.kind for t in traces] == ["post", "thread"]
    assert traces[1].context.content == "shipping a thing today"
    assert all(t.source.tier == "first_party" for t in traces)


def test_firecrawl_crawl_polls_job(monkeypatch):
    calls = {"status": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/crawl" and request.method == "POST":
            return httpx.Response(200, json={"success": True, "id": "job-1"})
        if request.url.path == "/v1/crawl/job-1":
            calls["status"] += 1
            if calls["status"] < 2:
                return httpx.Response(200, json={"status": "scraping"})
            return httpx.Response(
                200,
                json={
                    "status": "completed",
                    "data": [
                        {
                            "markdown": "page one",
                            "metadata": {
                                "title": "One",
                                "sourceURL": "https://site.example/one",
                                "publishedDate": "2026-01-01T00:00:00Z",
                            },
                        },
                        {"markdown": "", "metadata": {}},
                    ],
                },
            )
        return httpx.Response(404)

    from peoplereadme.ingest import crawl_firecrawl

    client = httpx.Client(transport=httpx.MockTransport(handler))
    items, cursor = crawl_firecrawl(
        "https://site.example", client=client, poll_interval=0
    )
    assert len(items) == 1
    assert items[0].url == "https://site.example/one"
    assert items[0].tier == "press"
    assert cursor == "2026-01-01T00:00:00Z"
    assert calls["status"] == 2


def test_firecrawl_crawl_failed_job():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/crawl":
            return httpx.Response(200, json={"id": "job-2"})
        return httpx.Response(200, json={"status": "failed"})

    from peoplereadme.ingest import crawl_firecrawl

    client = httpx.Client(transport=httpx.MockTransport(handler))
    try:
        crawl_firecrawl("https://site.example", client=client, poll_interval=0)
    except ValueError as exc:
        assert "failed" in str(exc)
    else:
        raise AssertionError("expected ValueError")


class FakeLM:
    model = "fake"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def complete(self, system: str, user: str) -> str:
        self.calls += 1
        return self.responses.pop(0)


def _enrich_transport(scraped: list[str]):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/search":
            objective = json.loads(request.content)["objective"]
            if "round2" in objective:
                urls = [{"url": "https://deep.example/talk"}]
            else:
                urls = [
                    {"url": "https://blog.example/launch"},
                    {"url": "https://x.com/someone/status/1"},
                ]
            return httpx.Response(200, json={"results": urls})
        if request.url.path == "/v1/scrape":
            url = json.loads(request.content)["url"]
            scraped.append(url)
            return httpx.Response(
                200,
                json={
                    "data": {
                        "markdown": f"content of {url}",
                        "metadata": {"sourceURL": url, "title": "t"},
                    }
                },
            )
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def test_enrich_loop_recursion_and_skips(tmp_path, monkeypatch):
    monkeypatch.setenv("PARALLEL_API_KEY", "k")
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    scraped: list[str] = []
    client = httpx.Client(transport=_enrich_transport(scraped))
    lm = FakeLM(
        [
            '{"queries": ["round2 deeper"], "urls": ["https://blog.example/launch"]}',
            '{"queries": [], "urls": []}',
        ]
    )

    from peoplereadme.ingest import enrich

    report = enrich(
        tmp_path,
        "p",
        "Test Person",
        ["Test Person projects"],
        lm,
        max_rounds=3,
        max_pages=10,
        client=client,
    )
    # round 0 scrapes the blog post, skips x.com; round 1 follows the extracted
    # query and scrapes the deep talk; extracted duplicate URL is skipped
    assert scraped == ["https://blog.example/launch", "https://deep.example/talk"]
    assert report.total_new_items == 2
    assert len(report.rounds) == 2
    assert report.stopped_reason == "no new leads extracted"
    assert "https://x.com/someone/status/1" in report.rounds[0].skipped_urls
    items = load_evidence(tmp_path, "firecrawl")
    assert all(i.tier == "press" for i in items)
    log = json.loads((tmp_path / "evidence" / "enrichment.log.json").read_text())
    assert log[-1]["total_new_items"] == 2


def test_enrich_respects_page_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("PARALLEL_API_KEY", "k")
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    scraped: list[str] = []
    client = httpx.Client(transport=_enrich_transport(scraped))

    from peoplereadme.ingest import enrich

    report = enrich(
        tmp_path,
        "p",
        "Test Person",
        ["Test Person projects"],
        None,
        max_rounds=3,
        max_pages=1,
        client=client,
    )
    assert len(scraped) == 1
    assert report.total_new_items == 1
    assert report.stopped_reason == "no LM for lead extraction"


def test_enrich_stops_when_nothing_novel(tmp_path, monkeypatch):
    monkeypatch.setenv("PARALLEL_API_KEY", "k")
    monkeypatch.delenv("EXA_API_KEY", raising=False)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/search":
            return httpx.Response(
                200, json={"results": [{"url": "https://x.com/only/status/1"}]}
            )
        return httpx.Response(404)

    from peoplereadme.ingest import enrich

    client = httpx.Client(transport=httpx.MockTransport(handler))
    report = enrich(
        tmp_path,
        "p",
        "Test Person",
        ["Test Person"],
        None,
        max_rounds=3,
        max_pages=10,
        client=client,
    )
    assert report.total_new_items == 0
    assert report.stopped_reason == "no novel content this round"
    assert len(report.rounds) == 1
