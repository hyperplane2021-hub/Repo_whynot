from typing import Any, Literal

from pydantic import BaseModel, Field

SourceType = Literal["doc", "code", "issue", "pr", "commit", "tool"]
EvidenceGrade = Literal["high", "medium", "low", "irrelevant"]
EvidenceRole = Literal[
    "primary",
    "supporting",
    "background",
    "duplicate_candidate",
    "risk_signal",
]


class EvidenceItem(BaseModel):
    evidence_id: str | None = None
    source_type: SourceType
    title: str | None = None
    path: str | None = None
    url: str | None = None
    number: int | None = None
    start_line: int | None = None
    end_line: int | None = None
    snippet: str
    score: float | None = Field(default=None, ge=0)
    relevance_grade: EvidenceGrade | None = None
    role: EvidenceRole | None = None


class SupportedFact(BaseModel):
    text: str
    evidence_ids: list[str] = Field(default_factory=list)


class InferenceItem(BaseModel):
    text: str
    evidence_ids: list[str] = Field(default_factory=list)


class UncertaintyItem(BaseModel):
    text: str
    missing_evidence: list[str] = Field(default_factory=list)


class NodeTrace(BaseModel):
    request_id: str
    node_name: str
    model_used: str | None = None
    latency_ms: float
    input_evidence_count: int
    output_evidence_count: int
    fallback_used: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
