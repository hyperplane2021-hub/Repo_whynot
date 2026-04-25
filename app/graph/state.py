from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.rag.types import RetrievalResult
from app.schemas.common import EvidenceItem, NodeTrace
from app.schemas.planning import EvidenceGradeReport, QueryPlan

TaskType = Literal["auto", "issue_triage", "repo_qa", "not_supported_yet"]


class GraphState(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    repo_id: str
    task_type: TaskType = "auto"
    question: str = ""
    context: dict[str, Any] = Field(default_factory=dict)
    rewritten_queries: dict[str, str] = Field(default_factory=dict)
    query_plan: QueryPlan | None = None
    retrieval_results: list[RetrievalResult] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    candidate_evidence: list[EvidenceItem] = Field(default_factory=list)
    evidence_grade_report: EvidenceGradeReport | None = None
    planned_tools: list[dict[str, Any]] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    result: dict[str, Any] | None = None
    action_status: str = "read_only"
    trace: list[NodeTrace] = Field(default_factory=list)
    node_fallbacks: dict[str, bool] = Field(default_factory=dict)
    node_models: dict[str, str | None] = Field(default_factory=dict)
    node_metadata: dict[str, dict[str, Any]] = Field(default_factory=dict)
