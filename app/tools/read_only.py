import json
import subprocess
from pathlib import Path
from typing import Any

from app.rag.retrievers import tokenize
from app.tools.validation import clamp_limit, resolve_repo_path


def read_file(repo_root: Path, path: str, max_bytes: int = 100_000) -> dict[str, Any]:
    target = resolve_repo_path(repo_root, path)
    if not target.exists() or not target.is_file():
        raise FileNotFoundError(path)
    content = target.read_bytes()[:max_bytes].decode("utf-8", errors="replace")
    return {"path": path, "content": content, "line_count": content.count("\n") + bool(content)}


def grep_repo(
    repo_root: Path,
    query: str,
    path_glob: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    root = repo_root.resolve()
    terms = set(tokenize(query))
    if not terms:
        return []
    matches: list[dict[str, Any]] = []
    limit = clamp_limit(limit)
    candidates = root.glob(path_glob) if path_glob else root.rglob("*")
    for path in candidates:
        if not path.is_file() or _skip_file(path):
            continue
        rel = path.relative_to(root).as_posix()
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_number, line in enumerate(lines, start=1):
            if terms & set(tokenize(line + " " + rel)):
                matches.append({"path": rel, "line_number": line_number, "line_text": line.strip()})
                if len(matches) >= limit:
                    return matches
    return matches


def git_log(
    repo_root: Path,
    paths: list[str] | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    limit = clamp_limit(limit, maximum=50)
    cmd = [
        "git",
        "-C",
        str(repo_root.resolve()),
        "log",
        f"--max-count={limit}",
        "--name-only",
        "--pretty=format:%H%x1f%an%x1f%ad%x1f%s",
        "--date=iso",
    ]
    if paths:
        cmd.append("--")
        root = repo_root.resolve()
        for path in paths:
            cmd.append(str(resolve_repo_path(repo_root, path).relative_to(root)))
    try:
        proc = subprocess.run(cmd, check=False, text=True, capture_output=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    return _parse_git_log(proc.stdout)


def search_issues(
    repo_root: Path,
    query: str,
    state: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    issues_path = resolve_repo_path(repo_root, "issues.jsonl")
    if not issues_path.exists():
        return []
    terms = set(tokenize(query))
    results: list[dict[str, Any]] = []
    with issues_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            issue = json.loads(line)
            if state and issue.get("state") != state:
                continue
            haystack = " ".join(
                [
                    str(issue.get("title", "")),
                    str(issue.get("body", "")),
                    " ".join(issue.get("labels", []) or []),
                ]
            )
            score = len(terms & set(tokenize(haystack)))
            if score:
                results.append(
                    {
                        "number": issue.get("number"),
                        "title": issue.get("title"),
                        "state": issue.get("state"),
                        "labels": issue.get("labels", []),
                        "score": score,
                    }
                )
    return sorted(results, key=lambda item: item["score"], reverse=True)[: clamp_limit(limit)]


def _skip_file(path: Path) -> bool:
    return any(part in {".git", "__pycache__", ".pytest_cache"} for part in path.parts)


def _parse_git_log(output: str) -> list[dict[str, Any]]:
    commits: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in output.splitlines():
        if "\x1f" in line:
            if current:
                commits.append(current)
            sha, author, date, message = line.split("\x1f", 3)
            current = {"sha": sha, "author": author, "date": date, "message": message, "paths": []}
        elif line.strip() and current is not None:
            current["paths"].append(line.strip())
    if current:
        commits.append(current)
    return commits
