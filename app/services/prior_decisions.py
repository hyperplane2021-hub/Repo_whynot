from typing import Any

from app.github.ingest import load_ingested_issues
from app.rag.retrievers import tokenize
from app.schemas.common import EvidenceItem, InferenceItem, SupportedFact, UncertaintyItem
from app.schemas.prior_decision import PriorDecisionResult
from app.services.model_router import generate_json_result

DECISION_REJECTED = {"wontfix", "won't fix", "not planned", "declined", "rejected"}
DECISION_DEFERRED = {"deferred", "later", "future", "blocked"}
DECISION_ACCEPTED = {"accepted", "planned", "implemented", "fixed"}


def detect_prior_decision(repo: str, question: str, k: int = 8) -> PriorDecisionResult:
    issues = load_ingested_issues(repo)
    candidates = _rank_candidates(issues, question)[:k]
    fallback = _fallback_result(repo, question, candidates)
    llm_result = generate_json_result(
        instructions=(
            "You are Repo_whynot Prior Decision Detector. Return only valid JSON matching "
            "PriorDecisionResult. Decide whether the user's request or question appears "
            "to have a prior maintainer decision in the provided closed GitHub threads. "
            "Prefer explicit maintainer comments, labels, and closed canonical threads. "
            "Do not invent issue numbers or decisions. If evidence is weak, use unknown "
            "or prior_decision_found=false. Write suggested_response in the same language "
            "as the user's question, and do not mix in unexplained foreign-language words."
        ),
        payload={
            "repo": repo,
            "question": question,
            "candidate_threads": candidates,
            "local_fallback": fallback.model_dump(),
        },
        fallback=fallback.model_dump(),
        schema=PriorDecisionResult,
    )
    return PriorDecisionResult.model_validate(llm_result.data)


def _rank_candidates(issues: list[dict[str, Any]], question: str) -> list[dict[str, Any]]:
    question_tokens = set(tokenize(question))
    ranked: list[tuple[float, dict[str, Any]]] = []
    for issue in issues:
        text = _issue_text(issue)
        tokens = set(tokenize(text))
        score = len(question_tokens & tokens)
        score += _decision_signal_score(issue)
        if score > 0:
            ranked.append((score, issue))
    return [issue for _, issue in sorted(ranked, key=lambda item: item[0], reverse=True)]


def _fallback_result(
    repo: str,
    question: str,
    candidates: list[dict[str, Any]],
) -> PriorDecisionResult:
    evidence = [_issue_to_evidence(issue, index + 1) for index, issue in enumerate(candidates[:8])]
    status = _status_from_candidates(candidates)
    found = bool(candidates) and status != "unknown"
    canonical_threads = [issue["number"] for issue in candidates[:3]]
    supported = [
        SupportedFact(
            text=f"Closed thread #{issue['number']} may be relevant: {issue['title']}",
            evidence_ids=[f"E{index + 1}"],
        )
        for index, issue in enumerate(candidates[:3])
    ]
    return PriorDecisionResult(
        prior_decision_found=found,
        direct_decision_found=found,
        adjacent_decision_found=False,
        decision_status=status,
        decision_summary=_summary(status, candidates),
        reasoning=(
            "Rule-based fallback searched ingested closed GitHub issues for overlapping "
            "tokens plus decision labels and phrases."
        ),
        canonical_threads=canonical_threads,
        confidence="medium" if found and len(candidates) >= 2 else "low",
        suggested_response=_suggested_response(repo, question, status, canonical_threads),
        supported_facts=supported,
        inferences=[
            InferenceItem(
                text="These threads may represent prior maintainer context for the request.",
                evidence_ids=[item.evidence_id for item in evidence[:3] if item.evidence_id],
            )
        ]
        if candidates
        else [],
        uncertainties=[
            UncertaintyItem(
                text="Only locally ingested closed issues were searched.",
                missing_evidence=[
                    "open issues",
                    "pull request review threads",
                    "full comment history",
                ],
            )
        ],
        evidence=evidence,
    )


def _status_from_candidates(candidates: list[dict[str, Any]]) -> str:
    scores = {"rejected": 0, "deferred": 0, "accepted": 0, "duplicate": 0}
    for issue in candidates[:8]:
        labels = {str(label).lower() for label in issue.get("labels", [])}
        text = _issue_text(issue).lower()
        if "duplicate" in labels or "duplicate" in text:
            scores["duplicate"] += 2
        if labels & DECISION_REJECTED or any(phrase in text for phrase in DECISION_REJECTED):
            scores["rejected"] += 2
        if labels & DECISION_DEFERRED or any(phrase in text for phrase in DECISION_DEFERRED):
            scores["deferred"] += 1
        if labels & DECISION_ACCEPTED or any(phrase in text for phrase in DECISION_ACCEPTED):
            scores["accepted"] += 1
    status, score = max(scores.items(), key=lambda item: item[1])
    return status if score else "unknown"


def _decision_signal_score(issue: dict[str, Any]) -> float:
    labels = {str(label).lower() for label in issue.get("labels", [])}
    text = _issue_text(issue).lower()
    score = 0.0
    if labels & DECISION_REJECTED or any(phrase in text for phrase in DECISION_REJECTED):
        score += 5
    if "duplicate" in labels or "duplicate" in text:
        score += 4
    if labels & DECISION_DEFERRED or any(phrase in text for phrase in DECISION_DEFERRED):
        score += 2
    if "feature" in labels or "proposal" in text:
        score += 1
    return score


def _issue_to_evidence(issue: dict[str, Any], index: int) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=f"E{index}",
        source_type="issue",
        title=issue["title"],
        url=issue.get("url"),
        number=issue["number"],
        snippet=_snippet(_issue_text(issue)),
        relevance_grade="medium",
        role="primary" if index == 1 else "supporting",
    )


def _issue_text(issue: dict[str, Any]) -> str:
    comments = "\n".join(comment.get("body", "") for comment in issue.get("comments_sample", []))
    return "\n".join(
        [
            issue.get("title", ""),
            issue.get("body", ""),
            " ".join(issue.get("labels", [])),
            comments,
        ]
    )


def _summary(status: str, candidates: list[dict[str, Any]]) -> str:
    if not candidates:
        return "No relevant prior decision was found in the ingested issue set."
    title = candidates[0]["title"]
    if status == "unknown":
        return f"Relevant historical discussion was found, but no clear decision status: {title}"
    return (
        f"Likely prior decision status is {status}, "
        f"led by thread #{candidates[0]['number']}: {title}"
    )


def _suggested_response(repo: str, question: str, status: str, threads: list[int]) -> str:
    if not threads:
        return "No prior decision found in the ingested issue set; ask for maintainer review."
    thread_list = ", ".join(f"#{number}" for number in threads)
    return (
        f"This appears related to prior {repo} discussion(s) {thread_list}. "
        f"Current inferred status: {status}. Please review those threads before reopening."
    )


def _snippet(text: str, limit: int = 500) -> str:
    return " ".join(text.split())[:limit]
