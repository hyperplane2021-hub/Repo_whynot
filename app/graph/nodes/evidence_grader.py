from app.graph.state import GraphState
from app.schemas.planning import EvidenceGradeItem, EvidenceGradeReport
from app.services.model_router import generate_json_result


def evidence_grader(state: GraphState) -> GraphState:
    fallback_report = _fallback_grade_report(state)
    llm_result = generate_json_result(
        instructions=(
            "You are the Repo_whynot LLM Evidence Grader. Return only valid JSON matching "
            "EvidenceGradeReport. Grade each candidate evidence item as high, medium, "
            "low, or irrelevant. Mark exactly one role for each graded item: primary, "
            "supporting, background, duplicate_candidate, or risk_signal. Keep only "
            "evidence IDs that exist in the input. Follow the query plan's "
            "preferred_evidence and avoid_evidence when judging relevance."
        ),
        payload={
            "request_id": state.request_id,
            "task_type": state.task_type,
            "question": state.question,
            "context": state.context,
            "query_plan": state.query_plan.model_dump() if state.query_plan else None,
            "candidate_evidence": [item.model_dump() for item in state.candidate_evidence],
            "fallback_report": fallback_report.model_dump(),
        },
        fallback=fallback_report.model_dump(),
        schema=EvidenceGradeReport,
    )
    report = _sanitize_report(
        EvidenceGradeReport.model_validate(llm_result.data),
        {item.evidence_id for item in state.candidate_evidence if item.evidence_id},
    )
    state.evidence_grade_report = report
    by_id = {item.evidence_id: item for item in state.candidate_evidence if item.evidence_id}
    grade_by_id = {item.evidence_id: item for item in report.graded_evidence}
    kept = [by_id[evidence_id] for evidence_id in report.kept_evidence_ids if evidence_id in by_id]
    fallback_by_id = {
        item.evidence_id: item for item in _fallback_grade_report(state).graded_evidence
    }
    for item in kept:
        if item.evidence_id in grade_by_id:
            item.relevance_grade = grade_by_id[item.evidence_id].grade
            item.role = grade_by_id[item.evidence_id].role
        elif item.evidence_id in fallback_by_id:
            item.relevance_grade = fallback_by_id[item.evidence_id].grade
            item.role = fallback_by_id[item.evidence_id].role
    state.evidence = kept or state.candidate_evidence
    state.node_fallbacks["evidence_grader"] = llm_result.fallback_used
    state.node_models["evidence_grader"] = llm_result.model_used
    state.node_metadata["evidence_grader"] = {
        "kept": len(report.kept_evidence_ids),
        "rejected": len(report.rejected_evidence_ids),
        "missing_evidence": report.missing_evidence,
        "recommended_tool_checks": report.recommended_tool_checks,
    }
    return state


def _fallback_grade_report(state: GraphState) -> EvidenceGradeReport:
    graded: list[EvidenceGradeItem] = []
    kept: list[str] = []
    rejected: list[str] = []
    for item in state.candidate_evidence:
        if not item.evidence_id:
            continue
        role = "supporting"
        grade = "medium"
        if state.query_plan:
            preference_grade = _grade_from_preferences(item, state.query_plan)
            if preference_grade:
                grade, role = preference_grade
        if item.source_type == "code":
            role = "primary"
            grade = "high"
        elif state.task_type == "issue_triage" and item.source_type == "issue":
            role = "duplicate_candidate"
            grade = "high"
        elif item.source_type == "commit":
            role = "background"
        if item.score is not None and item.score < 1:
            grade = "low"
        graded.append(
            EvidenceGradeItem(
                evidence_id=item.evidence_id,
                grade=grade,  # type: ignore[arg-type]
                role=role,  # type: ignore[arg-type]
                rationale="Rule-based grade from source type and retrieval score.",
            )
        )
        if grade == "irrelevant":
            rejected.append(item.evidence_id)
        else:
            kept.append(item.evidence_id)
    return EvidenceGradeReport(
        graded_evidence=graded,
        kept_evidence_ids=kept,
        rejected_evidence_ids=rejected,
        missing_evidence=[],
        recommended_tool_checks=_recommended_tool_checks(state),
    )


def _grade_from_preferences(item, query_plan) -> tuple[str, str] | None:
    path = (item.path or "").lower()
    text = f"{path} {item.title or ''} {item.snippet}".lower()
    preferred = [preference.lower() for preference in query_plan.preferred_evidence]
    avoid = [preference.lower() for preference in query_plan.avoid_evidence]
    if any(_matches_preference(preference, text, path) for preference in avoid):
        return ("low", "background")
    if any(_matches_preference(preference, text, path) for preference in preferred):
        return ("high", "primary")
    return None


def _matches_preference(preference: str, text: str, path: str) -> bool:
    aliases = {
        "readme": ["readme"],
        "project metadata": ["pyproject.toml", "package.json", "setup.py", "setup.cfg"],
        "docs index": ["docs/index", "index.md", "index.rst"],
        "quickstart": ["quickstart"],
        "public api modules": ["__init__.py", "_api.py", "api.py"],
        "contributing guide": ["contributing"],
        "changelog": ["changelog", "changes"],
        "tests": ["tests/"],
    }
    needles = aliases.get(preference, [preference])
    return any(needle in path or needle in text for needle in needles)


def _recommended_tool_checks(state: GraphState) -> list[str]:
    checks: list[str] = []
    if any(item.path for item in state.candidate_evidence):
        checks.append("read_file")
    if state.task_type == "issue_triage":
        checks.append("search_issues")
    return checks


def _sanitize_report(report: EvidenceGradeReport, valid_ids: set[str]) -> EvidenceGradeReport:
    graded = [item for item in report.graded_evidence if item.evidence_id in valid_ids]
    kept = [item for item in report.kept_evidence_ids if item in valid_ids]
    rejected = [
        item for item in report.rejected_evidence_ids if item in valid_ids and item not in kept
    ]
    if not kept:
        kept = [item.evidence_id for item in graded if item.grade != "irrelevant"]
    return EvidenceGradeReport(
        graded_evidence=graded,
        kept_evidence_ids=kept,
        rejected_evidence_ids=rejected,
        missing_evidence=report.missing_evidence[:5],
        recommended_tool_checks=report.recommended_tool_checks[:5],
    )
