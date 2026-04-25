from app.schemas.common import EvidenceItem, SupportedFact
from app.schemas.repo_answer import RepoAnswer
from app.schemas.triage import IssueTriageResult


def test_core_schemas_validate() -> None:
    evidence = [EvidenceItem(source_type="doc", snippet="Auth docs")]
    IssueTriageResult(
        issue_category="bug",
        severity="medium",
        duplicate_likelihood=0.5,
        suggested_labels=["bug"],
        related_issues=[12],
        related_files=["src/auth/session.py"],
        recommended_next_action="Inspect the auth module.",
        reasoning_summary="Matches known token refresh behavior.",
        evidence=evidence,
    )
    RepoAnswer(
        answer="Token refresh lives in the auth session module.",
        confidence="high",
        affected_modules=["src/auth/session.py"],
        follow_up_questions=[],
        supported_facts=[SupportedFact(text="Auth lives in session.py.", evidence_ids=["E1"])],
        evidence=evidence,
    )
