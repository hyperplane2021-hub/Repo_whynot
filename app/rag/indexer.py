import json
from pathlib import Path

from app.config import get_settings
from app.rag.loaders import load_repo_documents
from app.rag.types import IndexDocument, IndexStats

INDEX_FILE = "documents.jsonl"
MANIFEST_FILE = "manifest.json"


def repo_id_to_dir(repo_id: str) -> str:
    return repo_id.replace("/", "_").replace(":", "_")


def index_path_for(repo_id: str, index_root: Path | None = None) -> Path:
    root = index_root or get_settings().index_root
    return Path(root) / repo_id_to_dir(repo_id)


def build_index(repo_path: Path, repo_id: str) -> IndexStats:
    documents = load_repo_documents(repo_path)
    index_path = index_path_for(repo_id)
    index_path.mkdir(parents=True, exist_ok=True)
    docs_file = index_path / INDEX_FILE
    with docs_file.open("w", encoding="utf-8") as handle:
        for document in documents:
            handle.write(document.model_dump_json() + "\n")

    docs_chunks = sum(1 for doc in documents if doc.source_type == "doc")
    code_chunks = sum(1 for doc in documents if doc.source_type == "code")
    history_chunks = len(documents) - docs_chunks - code_chunks
    manifest = {
        "repo_id": repo_id,
        "repo_path": str(repo_path),
        "docs_chunks": docs_chunks,
        "code_chunks": code_chunks,
        "history_chunks": history_chunks,
    }
    (index_path / MANIFEST_FILE).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return IndexStats(
        repo_id=repo_id,
        index_path=str(index_path),
        docs_chunks=docs_chunks,
        code_chunks=code_chunks,
        history_chunks=history_chunks,
    )


def load_index(repo_id: str) -> list[IndexDocument]:
    docs_file = index_path_for(repo_id) / INDEX_FILE
    if not docs_file.exists():
        raise FileNotFoundError(
            f"Index not found for repo_id={repo_id}. Run `repoops index` first."
        )
    documents: list[IndexDocument] = []
    with docs_file.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                documents.append(IndexDocument.model_validate_json(line))
    return documents


def load_manifest(repo_id: str) -> dict:
    manifest_file = index_path_for(repo_id) / MANIFEST_FILE
    if not manifest_file.exists():
        raise FileNotFoundError(
            f"Manifest not found for repo_id={repo_id}. Run `repoops index` first."
        )
    return json.loads(manifest_file.read_text(encoding="utf-8"))
