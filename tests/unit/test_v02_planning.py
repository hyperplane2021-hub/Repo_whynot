from pathlib import Path

from app.graph.builder import run_graph
from app.graph.state import GraphState
from app.rag.indexer import build_index
from app.schemas.planning import EvidenceGradeReport, QueryPlan


def test_query_plan_and_evidence_grading_fallback() -> None:
    build_index(Path("data/fixtures/sample_repo"), "sample/repo")
    state = run_graph(
        GraphState(
            repo_id="sample/repo",
            task_type="repo_qa",
            question="How does authentication refresh tokens?",
        )
    )

    assert isinstance(state.query_plan, QueryPlan)
    assert state.query_plan.docs_queries
    assert isinstance(state.evidence_grade_report, EvidenceGradeReport)
    assert all(item.evidence_id for item in state.evidence)
    assert all(item.relevance_grade for item in state.evidence)
    assert all(item.role for item in state.evidence)
    assert state.query_plan.intent_family in {
        "overview",
        "how_it_works",
        "where_is",
        "troubleshooting",
        "change_impact",
        "issue_triage",
        "usage",
        "unknown",
    }


def test_overview_preferences_promote_project_metadata() -> None:
    build_index(Path("data/fixtures/sample_repo"), "sample/repo")
    state = run_graph(
        GraphState(
            repo_id="sample/repo",
            task_type="repo_qa",
            question="What does this repository do?",
        )
    )
    assert state.query_plan
    assert state.query_plan.intent_family == "overview"
    assert "README" in state.query_plan.preferred_evidence


def test_trace_records_each_explicit_node() -> None:
    build_index(Path("data/fixtures/sample_repo"), "sample/repo")
    state = run_graph(
        GraphState(repo_id="sample/repo", task_type="repo_qa", question="Where is auth?")
    )

    node_names = [item.node_name for item in state.trace]
    assert "query_rewrite" in node_names
    assert "evidence_grader" in node_names
    assert "tool_planner" in node_names
    assert all(item.request_id == state.request_id for item in state.trace)


def test_tool_loop_obeys_call_limit(monkeypatch) -> None:
    monkeypatch.setenv("REPOOPS_MAX_TOOL_ROUNDS", "1")
    monkeypatch.setenv("REPOOPS_MAX_TOOL_CALLS_PER_ROUND", "1")
    from app.config import get_settings

    get_settings.cache_clear()
    build_index(Path("data/fixtures/sample_repo"), "sample/repo")
    state = run_graph(
        GraphState(
            repo_id="sample/repo",
            task_type="issue_triage",
            question="Login fails after token expires",
        )
    )
    assert len(state.tool_results) <= 1
    get_settings.cache_clear()
