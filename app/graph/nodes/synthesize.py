import re

from app.graph.state import GraphState
from app.schemas.common import InferenceItem, SupportedFact, UncertaintyItem
from app.schemas.repo_answer import RepoAnswer
from app.schemas.triage import IssueTriageResult
from app.services.model_router import generate_json_result

BUG_WORDS = ("fail", "fails", "error", "exception", "bug", "crash", "失败", "报错")
DOC_WORDS = ("doc", "docs", "documentation", "文档")
FEATURE_WORDS = ("feature", "add", "request", "支持", "新增")


def synthesize_output(state: GraphState) -> GraphState:
    if state.task_type == "issue_triage":
        result = _synthesize_triage(state)
    elif state.task_type == "repo_qa":
        result = _synthesize_answer(state)
    else:
        result = {"error": "not_supported_yet"}
    state.result = result
    return state


def _synthesize_triage(state: GraphState) -> dict:
    text = _request_text(state).lower()
    category = _category(text)
    category = _category(text)
    related_issues = _related_issues(state, category)
    related_files = sorted({item.path for item in state.evidence if item.path})
    duplicate_likelihood = _duplicate_likelihood(category, related_issues, text)
    labels = _labels(category, text, related_files)
    result = IssueTriageResult(
        issue_category=category,
        severity=_severity(text),
        duplicate_likelihood=round(duplicate_likelihood, 2),
        suggested_labels=labels,
        related_issues=related_issues,
        related_files=related_files,
        recommended_next_action=_next_action(category, related_issues, related_files),
        reasoning_summary=_triage_reasoning(category, related_issues, related_files),
        supported_facts=_supported_facts(state),
        inferences=_triage_inferences(category, related_issues, state),
        uncertainties=_uncertainties(state),
        evidence=state.evidence,
    )
    fallback = result.model_dump()
    llm_result = generate_json_result(
        instructions=(
            "You are RepoOps Maintainer Agent. Return only valid JSON matching the "
            "complete IssueTriageResult schema. Start from local_fallback and improve "
            "only text fields or reasoning fields supported by evidence. Keep the full "
            "evidence array unchanged. Do not invent files, issue numbers, labels, or "
            "remote actions. Cite evidence_id in every supported_facts and inferences "
            "item. Clearly separate supported facts, inferences, and uncertainties. "
            "Return exactly one complete JSON object with all required fields."
        ),
        payload={
            "request_id": state.request_id,
            "task": "issue_triage",
            "request": _request_text(state),
            "local_fallback": fallback,
            "tool_results": state.tool_results,
            "evidence_grade_report": (
                state.evidence_grade_report.model_dump() if state.evidence_grade_report else None
            ),
        },
        fallback=fallback,
        schema=IssueTriageResult,
    )
    state.node_fallbacks["synthesize_output"] = llm_result.fallback_used
    state.node_models["synthesize_output"] = llm_result.model_used
    data = _postprocess_triage(llm_result.data)
    state.node_metadata["synthesize_output"] = {"schema": "IssueTriageResult"}
    return data


def _synthesize_answer(state: GraphState) -> dict:
    modules = sorted({item.path for item in state.evidence if item.path})
    snippets = [item.snippet for item in state.evidence[:3]]
    answer = (
        "Based on the local docs, code, and history, "
        + (" ".join(snippets) if snippets else "there is not enough indexed evidence yet.")
    )
    result = RepoAnswer(
        answer=answer,
        confidence="high" if len(state.evidence) >= 3 else "medium" if state.evidence else "low",
        affected_modules=modules,
        follow_up_questions=[] if state.evidence else ["Which repository area should I inspect?"],
        supported_facts=_supported_facts(state),
        inferences=_answer_inferences(state),
        uncertainties=_uncertainties(state),
        evidence=state.evidence,
    )
    fallback = result.model_dump()
    llm_result = generate_json_result(
        instructions=(
            "You are RepoOps Maintainer Agent. Return only valid JSON matching the "
            "complete RepoAnswer schema. Start from local_fallback and improve the answer "
            "using only the provided local repository evidence. Keep the full evidence "
            "array unchanged. Do not invent facts. Cite evidence_id in every "
            "supported_facts and inferences item. Clearly separate supported facts, "
            "inferences, and uncertainties. Return exactly one complete JSON object with "
            "all required fields."
        ),
        payload={
            "request_id": state.request_id,
            "task": "repo_qa",
            "question": state.question,
            "local_fallback": fallback,
            "tool_results": state.tool_results,
            "evidence_grade_report": (
                state.evidence_grade_report.model_dump() if state.evidence_grade_report else None
            ),
        },
        fallback=fallback,
        schema=RepoAnswer,
    )
    state.node_fallbacks["synthesize_output"] = llm_result.fallback_used
    state.node_models["synthesize_output"] = llm_result.model_used
    state.node_metadata["synthesize_output"] = {"schema": "RepoAnswer"}
    return llm_result.data


def _request_text(state: GraphState) -> str:
    return " ".join(
        [
            state.question,
            str(state.context.get("issue_title", "")),
            str(state.context.get("issue_body", "")),
        ]
    )


def _category(text: str) -> str:
    if any(word in text for word in DOC_WORDS):
        return "docs"
    if any(word in text for word in FEATURE_WORDS):
        return "feature_request"
    if any(word in text for word in BUG_WORDS):
        return "bug"
    if "why" in text or "how" in text or "?" in text:
        return "question"
    return "unknown"


def _severity(text: str) -> str:
    if any(word in text for word in ("security", "data loss", "outage", "critical")):
        return "critical"
    if any(word in text for word in ("500", "crash", "cannot login", "can't login")):
        return "high"
    if any(word in text for word in BUG_WORDS):
        return "medium"
    return "low"


def _labels(category: str, text: str, related_files: list[str]) -> list[str]:
    labels = [category if category != "feature_request" else "feature"]
    if "auth" in text or any("auth" in path for path in related_files):
        labels.append("auth")
    if "api" in text or any("api" in path for path in related_files):
        labels.append("api")
    return sorted(set(labels))


def _similarity_bonus(text: str) -> float:
    return 0.25 if re.search(r"token|login|auth|refresh", text) else 0.0


def _next_action(category: str, related_issues: list[int], related_files: list[str]) -> str:
    if category == "docs":
        return "Confirm the documentation gap and update the relevant docs page."
    if category == "feature_request":
        return "Clarify scope and decide whether this belongs on the roadmap."
    if related_issues:
        return f"Compare against related issue #{related_issues[0]} before opening new work."
    if related_files:
        return f"Inspect {related_files[0]} and confirm the behavior with a focused test."
    return "Ask for a minimal reproduction and affected version."


def _triage_reasoning(category: str, related_issues: list[int], related_files: list[str]) -> str:
    parts = [f"The report looks like {category}."]
    if related_issues:
        parts.append(f"It overlaps with historical issue(s): {related_issues}.")
    if related_files:
        parts.append(f"Indexed evidence points at: {', '.join(related_files[:3])}.")
    return " ".join(parts)


def _supported_facts(state: GraphState) -> list[SupportedFact]:
    facts: list[SupportedFact] = []
    for item in state.evidence[:4]:
        if not item.evidence_id:
            continue
        if item.path:
            text = f"Relevant {item.source_type} evidence was found in {item.path}."
        elif item.number:
            text = f"Relevant {item.source_type} evidence was found in item #{item.number}."
        else:
            text = f"Relevant {item.source_type} evidence was found."
        facts.append(SupportedFact(text=text, evidence_ids=[item.evidence_id]))
    return facts


def _triage_inferences(
    category: str,
    related_issues: list[int],
    state: GraphState,
) -> list[InferenceItem]:
    evidence_ids = [item.evidence_id for item in state.evidence[:3] if item.evidence_id]
    inferences = [
        InferenceItem(
            text=f"The issue is best categorized as {category} based on matching evidence.",
            evidence_ids=evidence_ids,
        )
    ]
    if related_issues:
        inferences.append(
            InferenceItem(
                text="The issue may duplicate or overlap with prior local issue history.",
                evidence_ids=[
                    item.evidence_id
                    for item in state.evidence
                    if item.source_type == "issue" and item.evidence_id
                ],
            )
        )
    return inferences


def _answer_inferences(state: GraphState) -> list[InferenceItem]:
    evidence_ids = [item.evidence_id for item in state.evidence[:3] if item.evidence_id]
    if not evidence_ids:
        return []
    return [
        InferenceItem(
            text="The answer is synthesized from the highest-ranked local repository evidence.",
            evidence_ids=evidence_ids,
        )
    ]


def _uncertainties(state: GraphState) -> list[UncertaintyItem]:
    missing = []
    if state.evidence_grade_report:
        missing = state.evidence_grade_report.missing_evidence
    if not missing and not state.evidence:
        missing = ["No local evidence was retrieved."]
    return [UncertaintyItem(text=item, missing_evidence=[item]) for item in missing[:3]]


def _related_issues(state: GraphState, category: str) -> list[int]:
    numbers: list[int] = []
    for item in state.evidence:
        if item.source_type != "issue" or item.number is None:
            continue
        haystack = f"{item.title or ''} {item.snippet}".lower()
        if category == "docs" and not any(word in haystack for word in ("doc", "docs")):
            continue
        if category == "bug" and not any(
            word in haystack for word in ("bug", "fail", "fails", "error", "500")
        ):
            continue
        if category == "feature_request" and not any(
            word in haystack for word in ("feature", "add", "request")
        ):
            continue
        numbers.append(item.number)
    return sorted(set(numbers))


def _duplicate_likelihood(category: str, related_issues: list[int], text: str) -> float:
    if category in {"docs", "feature_request", "question"}:
        base = 0.15
        return round(min(0.65, base + 0.15 * len(related_issues)), 2)
    return round(min(0.95, 0.25 + (0.2 * len(related_issues)) + _similarity_bonus(text)), 2)


def _postprocess_triage(data: dict) -> dict:
    category = data.get("issue_category")
    if category in {"docs", "feature_request", "question"}:
        data["duplicate_likelihood"] = min(float(data.get("duplicate_likelihood", 0)), 0.65)
    if category == "docs":
        data["recommended_next_action"] = (
            "Confirm the documentation gap and update the relevant docs page."
        )
    return data
