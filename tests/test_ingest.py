"""Ingestion tests: X archive zip, GitHub (mock transport), RSS/Atom, file drops."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import httpx

from peoplereadme.evidence import append_evidence, load_evidence, load_sources_lock
from peoplereadme.ingest import ingest_file, ingest_github, ingest_rss, ingest_x_archive
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


def test_file_ingest(tmp_path: Path):
    drop = tmp_path / "talk.md"
    drop.write_text("# Talk transcript\nhello")
    items, cursor = ingest_file(drop)
    assert len(items) == 1
    assert items[0].source == "file"
    assert items[0].content.startswith("# Talk transcript")
    assert cursor == items[0].timestamp
