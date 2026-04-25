from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import EvidenceGrade, EvidenceRole


class QueryPlan(BaseModel):
    intent_family: Literal[
        "overview",
        "how_it_works",
        "where_is",
        "troubleshooting",
        "change_impact",
        "issue_triage",
        "usage",
        "unknown",
    ] = "unknown"
    intent_description: str = ""
    docs_queries: list[str] = Field(default_factory=list)
    code_queries: list[str] = Field(default_factory=list)
    history_queries: list[str] = Field(default_factory=list)
    preferred_evidence: list[str] = Field(default_factory=list)
    avoid_evidence: list[str] = Field(default_factory=list)
    likely_modules: list[str] = Field(default_factory=list)
    likely_files: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    search_strategy: str = "keyword"

    @field_validator(
        "docs_queries",
        "code_queries",
        "history_queries",
        "preferred_evidence",
        "avoid_evidence",
        "likely_modules",
        "likely_files",
        "keywords",
        mode="after",
    )
    @classmethod
    def dedupe_nonempty(cls, values: list[str]) -> list[str]:
        seen: set[str] = set()
        cleaned: list[str] = []
        for value in values:
            stripped = value.strip()
            if stripped and stripped not in seen:
                seen.add(stripped)
                cleaned.append(stripped)
        return cleaned[:8]


class EvidenceGradeItem(BaseModel):
    evidence_id: str
    grade: EvidenceGrade
    role: EvidenceRole
    rationale: str = ""


class EvidenceGradeReport(BaseModel):
    graded_evidence: list[EvidenceGradeItem] = Field(default_factory=list)
    kept_evidence_ids: list[str] = Field(default_factory=list)
    rejected_evidence_ids: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    recommended_tool_checks: list[str] = Field(default_factory=list)


AllowedToolName = Literal["read_file", "grep_repo", "git_log", "search_issues"]


class PlannedToolCall(BaseModel):
    tool_name: AllowedToolName
    arguments: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""
    evidence_ids: list[str] = Field(default_factory=list)


class ToolPlan(BaseModel):
    calls: list[PlannedToolCall] = Field(default_factory=list)
    rationale: str = ""
