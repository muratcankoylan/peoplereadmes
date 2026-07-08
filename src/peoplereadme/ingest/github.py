"""GitHub ingestion via the public REST API: repos, commit messages, public events."""

from __future__ import annotations

import os

import httpx

from ..evidence import EvidenceItem

API = "https://api.github.com"


def _client(client: httpx.Client | None) -> httpx.Client:
    if client is not None:
        return client
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.Client(headers=headers, timeout=30)


def _repo_items(client: httpx.Client, user: str, max_repos: int) -> list[EvidenceItem]:
    resp = client.get(
        f"{API}/users/{user}/repos",
        params={"sort": "pushed", "per_page": max_repos, "type": "owner"},
    )
    resp.raise_for_status()
    items = []
    for repo in resp.json():
        if repo.get("fork"):
            continue
        items.append(
            EvidenceItem(
                source="github",
                url=repo["html_url"],
                timestamp=repo["created_at"],
                content=f"{repo['name']}: {repo.get('description') or ''}".strip(),
                kind="project",
                extra={"repo": repo["full_name"], "language": repo.get("language")},
            )
        )
    return items


def _commit_items(
    client: httpx.Client, user: str, repo_full_name: str, per_repo: int
) -> list[EvidenceItem]:
    resp = client.get(
        f"{API}/repos/{repo_full_name}/commits",
        params={"author": user, "per_page": per_repo},
    )
    if resp.status_code in (404, 409):  # empty or missing repo
        return []
    resp.raise_for_status()
    items = []
    for commit in resp.json():
        items.append(
            EvidenceItem(
                source="github",
                url=commit["html_url"],
                timestamp=commit["commit"]["author"]["date"],
                content=commit["commit"]["message"],
                kind="commit",
                extra={"repo": repo_full_name, "sha": commit["sha"]},
            )
        )
    return items


def ingest_github(
    user: str,
    client: httpx.Client | None = None,
    max_repos: int = 30,
    commits_per_repo: int = 50,
) -> tuple[list[EvidenceItem], str]:
    """Returns (items, cursor). Cursor is the newest item timestamp seen."""
    owns_client = client is None
    client = _client(client)
    try:
        items = _repo_items(client, user, max_repos)
        for repo_item in list(items):
            items.extend(
                _commit_items(client, user, repo_item.extra["repo"], commits_per_repo)
            )
    finally:
        if owns_client:
            client.close()
    items.sort(key=lambda i: i.timestamp)
    cursor = items[-1].timestamp if items else ""
    return items, cursor
