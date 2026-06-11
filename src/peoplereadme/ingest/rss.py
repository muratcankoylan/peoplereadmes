"""RSS / Atom feed ingestion (parsed with defusedxml to guard against hostile feeds)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx
from defusedxml.ElementTree import fromstring as defused_fromstring

from ..evidence import EvidenceItem

_ATOM = "{http://www.w3.org/2005/Atom}"


_EPOCH = datetime(1970, 1, 1, tzinfo=UTC).isoformat()


def _iso(value: str | None) -> str:
    """Always returns a valid ISO timestamp; unparseable dates fall back to the epoch."""
    if not value:
        return _EPOCH
    try:
        return parsedate_to_datetime(value).astimezone(UTC).isoformat()
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return _EPOCH


def _rss_items(channel: ET.Element) -> list[EvidenceItem]:
    items = []
    for item in channel.iter("item"):
        title = item.findtext("title") or ""
        description = item.findtext("description") or ""
        items.append(
            EvidenceItem(
                source="rss",
                url=item.findtext("link") or "",
                timestamp=_iso(item.findtext("pubDate")),
                content=f"{title}\n\n{description}".strip(),
                kind="article",
                extra={"title": title},
            )
        )
    return items


def _atom_items(feed: ET.Element) -> list[EvidenceItem]:
    items = []
    for entry in feed.iter(f"{_ATOM}entry"):
        title = entry.findtext(f"{_ATOM}title") or ""
        body = entry.findtext(f"{_ATOM}summary") or entry.findtext(f"{_ATOM}content") or ""
        link = entry.find(f"{_ATOM}link")
        items.append(
            EvidenceItem(
                source="rss",
                url=link.get("href", "") if link is not None else "",
                timestamp=_iso(
                    entry.findtext(f"{_ATOM}published") or entry.findtext(f"{_ATOM}updated")
                ),
                content=f"{title}\n\n{body}".strip(),
                kind="article",
                extra={"title": title},
            )
        )
    return items


def parse_feed(xml_text: str) -> list[EvidenceItem]:
    root = defused_fromstring(xml_text)
    if root.tag == f"{_ATOM}feed":
        return _atom_items(root)
    return _rss_items(root)


def ingest_rss(url: str, client: httpx.Client | None = None) -> tuple[list[EvidenceItem], str]:
    """Returns (items, cursor). Cursor is the newest item timestamp seen."""
    client = client or httpx.Client(timeout=30, follow_redirects=True)
    resp = client.get(url)
    resp.raise_for_status()
    items = parse_feed(resp.text)
    items.sort(key=lambda i: i.timestamp)
    cursor = items[-1].timestamp if items else ""
    return items, cursor
