from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from app.rag.indexer import build_index

router = APIRouter()


class IndexRequest(BaseModel):
    repo_id: str
    repo_path: str


@router.post("/index")
def index_repo(request: IndexRequest) -> dict:
    stats = build_index(Path(request.repo_path), request.repo_id)
    return {
        "repo_id": stats.repo_id,
        "status": "indexed",
        "docs_chunks": stats.docs_chunks,
        "code_chunks": stats.code_chunks,
        "history_chunks": stats.history_chunks,
    }

