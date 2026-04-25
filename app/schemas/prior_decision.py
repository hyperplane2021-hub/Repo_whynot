from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import EvidenceItem, InferenceItem, SupportedFact, UncertaintyItem


class PriorDecisionResult(BaseModel):
    prior_decision_found: bool
    direct_decision_found: bool = False
    adjacent_decision_found: bool = False
    decision_status: Literal["accepted", "rejected", "deferred", "duplicate", "unknown"]
    decision_summary: str
    reasoning: str
    canonical_threads: list[int] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"]
    suggested_response: str
    supported_facts: list[SupportedFact] = Field(default_factory=list)
    inferences: list[InferenceItem] = Field(default_factory=list)
    uncertainties: list[UncertaintyItem] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)


class InvestigationQueryPlan(BaseModel):
    queries: list[str] = Field(default_factory=list)
    rationale: str = ""


class ThreadAssessment(BaseModel):
    number: int
    relevance: Literal["direct_decision", "adjacent_decision", "unrelated"]
    decision_status: Literal["accepted", "rejected", "deferred", "duplicate", "unknown"]
    rationale: str = ""


class InvestigationRoundTrace(BaseModel):
    round: int
    queries: list[str] = Field(default_factory=list)
    threads_found: list[int] = Field(default_factory=list)
    assessments: list[ThreadAssessment] = Field(default_factory=list)
    next_action: Literal["stop", "search_more", "synthesize"] = "synthesize"
    fallback_used: bool = False
