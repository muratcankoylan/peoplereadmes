"""Parse the official X (Twitter) export zip into normalized evidence items.

The archive ships tweets as `data/tweets.js` (or legacy `data/tweet.js`) containing
`window.YTD.tweets.part0 = [...]`. No API dependency.
"""

from __future__ import annotations

import json
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from ..evidence import EvidenceItem

_JS_PREFIX = re.compile(r"^window\.YTD\.[\w.]+\s*=\s*", re.DOTALL)
_CREATED_AT = "%a %b %d %H:%M:%S %z %Y"


def _parse_js_payload(text: str) -> list[dict]:
    return json.loads(_JS_PREFIX.sub("", text.strip()))


def _tweet_kind(tweet: dict) -> str:
    if tweet.get("in_reply_to_status_id_str"):
        return "reply"
    if tweet.get("full_text", "").startswith("RT @"):
        return "repost"
    return "post"


def _normalize_tweet(tweet: dict, username: str) -> EvidenceItem:
    created = datetime.strptime(tweet["created_at"], _CREATED_AT).astimezone(UTC)
    tweet_id = tweet["id_str"]
    return EvidenceItem(
        source="x-archive",
        url=f"https://x.com/{username}/status/{tweet_id}",
        timestamp=created.isoformat(),
        content=tweet.get("full_text", ""),
        kind=_tweet_kind(tweet),
        extra={
            "tweet_id": tweet_id,
            "in_reply_to_status_id": tweet.get("in_reply_to_status_id_str"),
            "in_reply_to_screen_name": tweet.get("in_reply_to_screen_name"),
        },
    )


def ingest_x_archive(zip_path: Path) -> tuple[list[EvidenceItem], str]:
    """Returns (items, cursor). Cursor is the newest tweet timestamp seen."""
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        username = "i"
        account_name = next(
            (n for n in names if n.endswith("data/account.js") or n == "account.js"), None
        )
        if account_name:
            accounts = _parse_js_payload(zf.read(account_name).decode("utf-8"))
            username = accounts[0].get("account", {}).get("username", username)

        tweet_files = [
            n
            for n in names
            if re.search(r"(^|/)tweets?(-part\d+)?\.js$", n) and "manifest" not in n
        ]
        if not tweet_files:
            raise ValueError(f"No tweets.js found in archive {zip_path}")

        items: list[EvidenceItem] = []
        for name in sorted(tweet_files):
            for entry in _parse_js_payload(zf.read(name).decode("utf-8")):
                tweet = entry.get("tweet", entry)
                items.append(_normalize_tweet(tweet, username))

    items.sort(key=lambda i: i.timestamp)
    cursor = items[-1].timestamp if items else ""
    return items, cursor
