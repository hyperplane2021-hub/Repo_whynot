import json
from collections.abc import Iterable
from pathlib import Path

from app.rag.chunkers import CODE_EXTENSIONS, chunk_code, chunk_markdown
from app.rag.types import IndexDocument


def load_repo_documents(repo_path: Path) -> list[IndexDocument]:
    repo_root = repo_path.resolve()
    docs: list[IndexDocument] = []
    for path in _iter_files(repo_root):
        if _is_ignored(path):
            continue
        if path.suffix == ".md":
            docs.extend(chunk_markdown(path, repo_root))
        elif path.suffix in CODE_EXTENSIONS:
            docs.extend(chunk_code(path, repo_root))
    docs.extend(load_history_documents(repo_root))
    return docs


def load_history_documents(repo_root: Path) -> list[IndexDocument]:
    documents: list[IndexDocument] = []
    for filename, source_type in [
        ("issues.jsonl", "issue"),
        ("prs.jsonl", "pr"),
        ("commits.jsonl", "commit"),
    ]:
        path = repo_root / filename
        if not path.exists():
            continue
        for row_number, item in enumerate(_read_jsonl(path), start=1):
            text = _history_text(item)
            documents.append(
                IndexDocument(
                    id=f"{source_type}:{item.get('number') or item.get('sha') or row_number}",
                    source_type=source_type,  # type: ignore[arg-type]
                    text=text,
                    metadata={"source_type": source_type, **item},
                )
            )
    return documents


def _iter_files(repo_root: Path) -> Iterable[Path]:
    for path in repo_root.rglob("*"):
        if path.is_file():
            yield path


def _is_ignored(path: Path) -> bool:
    return any(part in {".git", "__pycache__", ".pytest_cache"} for part in path.parts)


def _read_jsonl(path: Path) -> Iterable[dict]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _history_text(item: dict) -> str:
    fields = [
        str(item.get("title", "")),
        str(item.get("body", "")),
        str(item.get("message", "")),
        " ".join(item.get("labels", []) or []),
        " ".join(item.get("paths", []) or []),
    ]
    return "\n".join(field for field in fields if field).strip()

