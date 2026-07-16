"""X API v2 ingestion for recent tweets."""

from __future__ import annotations

import os

import httpx

from ..evidence import EvidenceItem

API = "https://api.x.com/2"


def _client(client: httpx.Client | None) -> httpx.Client:
    if client is not None:
        return client
    token = os.environ.get("X_BEARER_TOKEN")
    if not token:
        raise ValueError("Set X_BEARER_TOKEN to ingest X API tweets.")
    return httpx.Client(
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        timeout=30,
    )


def _tweet_kind(tweet: dict) -> str:
    refs = tweet.get("referenced_tweets") or []
    ref_types = {ref.get("type") for ref in refs}
    if "replied_to" in ref_types or tweet.get("in_reply_to_user_id"):
        return "reply"
    if "retweeted" in ref_types:
        return "repost"
    return "post"


def _reply_info(tweet: dict, includes: dict) -> tuple[str | None, str | None]:
    refs = tweet.get("referenced_tweets") or []
    replied_to = next((ref for ref in refs if ref.get("type") == "replied_to"), None)
    if replied_to is None:
        return None, None
    ref_id = replied_to.get("id")
    screen_name = None
    if ref_id:
        for ref_tweet in includes.get("tweets", []):
            if ref_tweet.get("id") == ref_id:
                author_id = ref_tweet.get("author_id")
                if author_id:
                    for user in includes.get("users", []):
                        if user.get("id") == author_id:
                            screen_name = user.get("username")
                            break
                break
    return ref_id, screen_name


def _normalize_tweet(tweet: dict, username: str, includes: dict) -> EvidenceItem:
    tweet_id = tweet["id"]
    timestamp = tweet["created_at"]
    in_reply_to_status_id, in_reply_to_screen_name = _reply_info(tweet, includes)
    return EvidenceItem(
        source="x-api",
        url=f"https://x.com/{username}/status/{tweet_id}",
        timestamp=timestamp,
        content=tweet.get("text", ""),
        kind=_tweet_kind(tweet),
        tier="first_party",
        extra={
            "tweet_id": tweet_id,
            "in_reply_to_status_id": in_reply_to_status_id,
            "in_reply_to_screen_name": in_reply_to_screen_name,
        },
    )


def ingest_x_api(
    username: str,
    client: httpx.Client | None = None,
    max_results: int = 1000,
) -> tuple[list[EvidenceItem], str]:
    """Returns (items, cursor). Cursor is the newest tweet timestamp seen.

    Paginates the user timeline until max_results tweets or the API runs out.
    Raises ValueError when the account verifiably has zero tweets so callers
    can distinguish "empty account" from a connector failure.
    """
    owns_client = client is None
    client = _client(client)
    items: list[EvidenceItem] = []
    try:
        user_resp = client.get(
            f"{API}/users/by/username/{username}",
            params={"user.fields": "public_metrics"},
        )
        user_resp.raise_for_status()
        user_payload = user_resp.json()
        user = user_payload.get("data") or {}
        user_id = user.get("id")
        if not user_id:
            errors = user_payload.get("errors") or [{}]
            detail = errors[0].get("detail", "no user id in response")
            raise ValueError(f"X user lookup failed for {username!r}: {detail}")
        tweet_count = (user.get("public_metrics") or {}).get("tweet_count")
        if tweet_count == 0:
            raise ValueError(
                f"X account @{username} has zero tweets according to the API "
                "(nothing to ingest; check the handle)"
            )

        pagination_token: str | None = None
        while len(items) < max_results:
            params: dict = {
                "max_results": min(max_results - len(items), 100),
                "tweet.fields": (
                    "created_at,author_id,conversation_id,"
                    "in_reply_to_user_id,referenced_tweets"
                ),
                "expansions": "author_id,referenced_tweets.id",
                "user.fields": "username",
            }
            if params["max_results"] < 5:
                break  # API rejects max_results < 5
            if pagination_token:
                params["pagination_token"] = pagination_token
            tweets_resp = client.get(f"{API}/users/{user_id}/tweets", params=params)
            tweets_resp.raise_for_status()
            payload = tweets_resp.json()
            includes = payload.get("includes", {})
            items.extend(
                _normalize_tweet(tweet, username, includes)
                for tweet in payload.get("data", [])
            )
            pagination_token = (payload.get("meta") or {}).get("next_token")
            if not pagination_token:
                break
    finally:
        if owns_client:
            client.close()
    items.sort(key=lambda item: item.timestamp)
    cursor = items[-1].timestamp if items else ""
    return items, cursor
