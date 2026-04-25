import json
import time
from pathlib import Path
from typing import Any

from openai import OpenAI

from app.config import get_settings
from app.graph.builder import run_query
from app.rag.indexer import build_index
from app.rag.retrievers import tokenize

CASES = [
    {
        "name": "rich_overview_cn",
        "repo_id": "real/rich",
        "repo_path": Path("/root/test-repos/rich"),
        "question": "我们这个repo是在干什么?",
    },
    {
        "name": "httpx_async",
        "repo_id": "real/httpx",
        "repo_path": Path("/root/test-repos/httpx"),
        "question": "How does HTTPX handle async clients and request sending?",
    },
    {
        "name": "click_groups",
        "repo_id": "real/click",
        "repo_path": Path("/root/test-repos/click"),
        "question": "How does Click implement command groups and option parsing?",
    },
]


def main() -> None:
    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)
    for case in CASES:
        print(f"\n\n===== {case['name']} =====")
        build_index(case["repo_path"], case["repo_id"])

        repoops_start = time.perf_counter()
        repoops = run_query(case["repo_id"], case["question"], "repo_qa")
        repoops_ms = (time.perf_counter() - repoops_start) * 1000

        direct_context = _direct_context(case["repo_path"], case["question"])
        direct_start = time.perf_counter()
        direct = _direct_answer(client, settings.model_name, case["question"], direct_context)
        direct_ms = (time.perf_counter() - direct_start) * 1000

        print("\n--- Direct Model ---")
        print(f"latency_ms: {direct_ms:.0f}")
        print(f"context_files: {', '.join(direct_context['included_files'])}")
        print(direct["answer"])

        print("\n--- RepoOps ---")
        print(f"latency_ms: {repoops_ms:.0f}")
        print(repoops["result"]["answer"])
        print("evidence:")
        for item in repoops["result"].get("evidence", [])[:5]:
            label = item.get("path") or item.get("title")
            print(
                "  - "
                f"{item.get('evidence_id')} {item.get('source_type')} "
                f"{item.get('relevance_grade')}/{item.get('role')} {label}"
            )
        print("trace:")
        for trace in repoops["trace"]:
            model = trace["model_used"] or "local"
            status = "fallback" if trace["fallback_used"] else "ok"
            print(f"  - {trace['node_name']}: {model} {status} {trace['latency_ms']:.0f}ms")


def _direct_answer(
    client: OpenAI,
    model: str,
    question: str,
    context: dict[str, Any],
) -> dict[str, str]:
    response = client.responses.create(
        model=model,
        instructions=(
            "Answer the user's repository question using only the provided compressed "
            "repository context. Be concise. If evidence is missing, say so."
        ),
        input=json.dumps(
            {"question": question, "repository_context": context},
            ensure_ascii=False,
        ),
        text={
            "format": {
                "type": "json_schema",
                "name": "DirectRepoAnswer",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"answer": {"type": "string"}},
                    "required": ["answer"],
                },
                "strict": True,
            }
        },
        max_output_tokens=1200,
    )
    return json.loads(response.output_text)


def _direct_context(repo_path: Path, question: str) -> dict[str, Any]:
    tree = _repo_tree(repo_path)
    included: dict[str, str] = {}
    for rel in ("README.md", "pyproject.toml", "package.json", "docs/index.md", "docs/index.rst"):
        path = repo_path / rel
        if path.exists() and path.is_file():
            included[rel] = _read_limited(path)

    for rel in _keyword_files(repo_path, question, limit=5):
        included.setdefault(rel, _read_limited(repo_path / rel, max_chars=3500))

    return {
        "tree_sample": tree,
        "included_files": list(included.keys()),
        "files": included,
    }


def _repo_tree(repo_path: Path, limit: int = 220) -> list[str]:
    paths: list[str] = []
    for path in sorted(repo_path.rglob("*")):
        if len(paths) >= limit:
            break
        if path.is_file() and not _skip(path):
            paths.append(path.relative_to(repo_path).as_posix())
    return paths


def _keyword_files(repo_path: Path, question: str, limit: int) -> list[str]:
    terms = set(tokenize(question))
    scored: list[tuple[int, str]] = []
    for path in repo_path.rglob("*"):
        if not path.is_file() or _skip(path) or path.suffix not in {".py", ".md", ".rst", ".toml"}:
            continue
        rel = path.relative_to(repo_path).as_posix()
        text = _read_limited(path, max_chars=6000).lower()
        score = len(terms & set(tokenize(rel + " " + text)))
        if score:
            scored.append((score, rel))
    return [rel for _, rel in sorted(scored, reverse=True)[:limit]]


def _read_limited(path: Path, max_chars: int = 6000) -> str:
    return path.read_text(encoding="utf-8", errors="replace")[:max_chars]


def _skip(path: Path) -> bool:
    return any(part in {".git", ".venv", "__pycache__", ".pytest_cache"} for part in path.parts)


if __name__ == "__main__":
    main()
