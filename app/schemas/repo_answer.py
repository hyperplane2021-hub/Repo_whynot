from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import EvidenceItem, InferenceItem, SupportedFact, UncertaintyItem


class RepoAnswer(BaseModel):
    answer: str
    confidence: Literal["low", "medium", "high"]
    affected_modules: list[str]
    follow_up_questions: list[str]
    supported_facts: list[SupportedFact] = Field(default_factory=list)
    inferences: list[InferenceItem] = Field(default_factory=list)
    uncertainties: list[UncertaintyItem] = Field(default_factory=list)
    evidence: list[EvidenceItem]
