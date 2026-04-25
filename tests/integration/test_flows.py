from pathlib import Path

from app.graph.builder import run_query
from app.rag.indexer import build_index
from app.schemas.repo_answer import RepoAnswer
from app.schemas.triage import IssueTriageResult


def test_index_triage_and_qa_flow() -> None:
    build_index(Path("data/fixtures/sample_repo"), "sample/repo")

    triage = run_query(
        "sample/repo",
        "Login fails after token expires",
        "issue_triage",
        {"issue_body": "Users are logged out when refresh token expires."},
    )
    parsed_triage = IssueTriageResult.model_validate(triage["result"])
    assert parsed_triage.issue_category == "bug"
    assert parsed_triage.evidence
    assert parsed_triage.supported_facts
    assert parsed_triage.supported_facts[0].evidence_ids

    answer = run_query("sample/repo", "How does authentication handle token refresh?", "repo_qa")
    parsed_answer = RepoAnswer.model_validate(answer["result"])
    assert parsed_answer.evidence
    assert answer["trace"]
    assert parsed_answer.supported_facts
