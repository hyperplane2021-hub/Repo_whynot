from typing import Any, Literal

from pydantic import BaseModel, Field


class IndexDocument(BaseModel):
    id: str
    source_type: Literal["doc", "code", "issue", "pr", "commit"]
    text: str
    metadata: dict[str, Any]


class RetrievalResult(BaseModel):
    document: IndexDocument
    score: float = Field(ge=0)


class IndexStats(BaseModel):
    repo_id: str
    index_path: str
    docs_chunks: int
    code_chunks: int
    history_chunks: int

