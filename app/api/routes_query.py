from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.graph.builder import run_query

router = APIRouter()


class QueryRequest(BaseModel):
    repo_id: str
    task_type: Literal["auto", "issue_triage", "repo_qa"] = "auto"
    question: str
    context: dict[str, Any] = Field(default_factory=dict)


@router.post("/query")
def query(request: QueryRequest) -> dict:
    return run_query(
        repo_id=request.repo_id,
        question=request.question,
        task_type=request.task_type,
        context=request.context,
    )

