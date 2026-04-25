import json
import time
import urllib.parse
import urllib.request
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.error import HTTPError

from app.config import get_settings, project_root

DECISION_SEARCH_TERMS = [
    "wontfix",
    "\"won't fix\"",
    '"not planned"',
    "declined",
    "rejected",
    "deferred",
    "duplicate",
    '"feature request"',
    "proposal",
]


class GitHubIngestError(RuntimeError):
    pass


def github_data_path(repo: str) -> Path:
    return project_root() / "data" / "github" / repo.replace("/", "_")


def ingest_github_issues(
    repo: str,
    limit: int = 100,
    query: str | None = None,
) -> dict[str, Any]:
    out_dir = github_data_path(repo)
    out_dir.mkdir(parents=True, exist_ok=True)
    issues = _fetch_search_issues(repo=repo, limit=limit, query=query)
    output = out_dir / "issues.jsonl"
    with output.open("w", encoding="utf-8") as handle:
        for issue in issues:
            handle.write(json.dumps(issue, ensure_ascii=False) + "\n")
    return {"repo": repo, "count": len(issues), "path": str(output)}


def search_github_issues(repo: str, query: str, limit: int = 10) -> list[dict[str, Any]]:
    if get_settings().github_search_cache:
        cached = _read_search_cache(repo, query, limit)
        if cached is not None:
            return cached
    issues = _fetch_search_issues(repo=repo, limit=limit, query=query)
    if get_settings().github_search_cache:
        _write_search_cache(repo, query, limit, issues)
    return issues


def load_ingested_issues(repo: str) -> list[dict[str, Any]]:
    path = github_data_path(repo) / "issues.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"No GitHub ingest found for {repo}. Run `repoops github ingest`.")
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _fetch_search_issues(repo: str, limit: int, query: str | None) -> list[dict[str, Any]]:
    terms = [query] if query else DECISION_SEARCH_TERMS
    by_number: dict[int, dict[str, Any]] = {}
    per_term = max(10, min(50, limit // max(1, len(terms)) + 5))
    for term in terms:
        if len(by_number) >= limit:
            break
        search_query = f"repo:{repo} is:issue is:closed {term}"
        url = "https://api.github.com/search/issues?" + urllib.parse.urlencode(
            {"q": search_query, "per_page": per_term}
        )
        data = _github_get(url)
        for item in data.get("items", []):
            if len(by_number) >= limit:
                break
            issue = _normalize_issue(item)
            issue["comments_sample"] = _fetch_comments_sample(item.get("comments_url"), limit=5)
            by_number[issue["number"]] = issue
        time.sleep(0.2)
    return list(by_number.values())


def _fetch_comments_sample(comments_url: str | None, limit: int) -> list[dict[str, Any]]:
    if not comments_url:
        return []
    data = _github_get(f"{comments_url}?per_page={limit}")
    comments: list[dict[str, Any]] = []
    for item in data[:limit]:
        comments.append(
            {
                "author": item.get("user", {}).get("login"),
                "body": item.get("body") or "",
                "created_at": item.get("created_at"),
            }
        )
    return comments


def _github_get(url: str) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "repoops-maintainer-agent",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = get_settings().github_token
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 403:
            raise GitHubIngestError(
                "GitHub API rate limit exceeded. Set REPOOPS_GITHUB_TOKEN in .env "
                "and retry the read-only ingest."
            ) from exc
        raise GitHubIngestError(f"GitHub API request failed: HTTP {exc.code}: {body}") from exc


def _normalize_issue(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "number": item["number"],
        "title": item.get("title") or "",
        "body": item.get("body") or "",
        "state": item.get("state"),
        "labels": [label.get("name") for label in item.get("labels", [])],
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
        "closed_at": item.get("closed_at"),
        "url": item.get("html_url"),
        "author": item.get("user", {}).get("login"),
    }


def _cache_path(repo: str, query: str, limit: int) -> Path:
    digest = sha256(f"{repo}|{query}|{limit}".encode()).hexdigest()[:24]
    return github_data_path(repo) / "search_cache" / f"{digest}.json"


def _read_search_cache(repo: str, query: str, limit: int) -> list[dict[str, Any]] | None:
    path = _cache_path(repo, query, limit)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_search_cache(repo: str, query: str, limit: int, issues: list[dict[str, Any]]) -> None:
    path = _cache_path(repo, query, limit)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(issues, ensure_ascii=False, indent=2), encoding="utf-8")
