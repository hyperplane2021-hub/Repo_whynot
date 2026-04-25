from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import EvidenceItem, InferenceItem, SupportedFact, UncertaintyItem


class IssueTriageResult(BaseModel):
    issue_category: Literal["bug", "feature_request", "docs", "support", "question", "unknown"]
    severity: Literal["low", "medium", "high", "critical", "unknown"]
    duplicate_likelihood: float = Field(ge=0, le=1)
    suggested_labels: list[str]
    related_issues: list[int]
    related_files: list[str]
    recommended_next_action: str
    reasoning_summary: str
    supported_facts: list[SupportedFact] = Field(default_factory=list)
    inferences: list[InferenceItem] = Field(default_factory=list)
    uncertainties: list[UncertaintyItem] = Field(default_factory=list)
    evidence: list[EvidenceItem]
