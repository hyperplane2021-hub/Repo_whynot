from app.schemas.prior_decision import PriorDecisionResult, ThreadAssessment
from app.services.prior_decision_investigator import (
    _calibrate_result_from_assessments,
    _calibrated_status,
    _fallback_assessment,
    _next_action,
    _query_expansions,
    _status_from_result_text,
)


def test_fallback_assessment_direct_rejected() -> None:
    assessment = _fallback_assessment(
        "Can we support HTML output?",
        {
            "number": 12,
            "title": "HTML output support",
            "body": "Maintainer declined this and marked it not planned.",
            "comments_sample": [],
        },
    )

    assert assessment.relevance == "direct_decision"
    assert assessment.decision_status == "rejected"


def test_next_action_search_more_for_adjacent() -> None:
    action = _next_action(
        [
            ThreadAssessment(
                number=12,
                relevance="adjacent_decision",
                decision_status="unknown",
            )
        ],
        round_number=1,
        max_rounds=2,
    )

    assert action == "search_more"


def test_calibrate_adjacent_result_lowers_confidence() -> None:
    result = PriorDecisionResult(
        prior_decision_found=True,
        direct_decision_found=True,
        adjacent_decision_found=False,
        decision_status="rejected",
        decision_summary="Decision found.",
        reasoning="Based on thread.",
        canonical_threads=[12],
        confidence="high",
        suggested_response="See #12.",
    )
    calibrated = _calibrate_result_from_assessments(
        result,
        [
            ThreadAssessment(
                number=12,
                relevance="adjacent_decision",
                decision_status="rejected",
            )
        ],
    )

    assert calibrated.direct_decision_found is False
    assert calibrated.adjacent_decision_found is True
    assert calibrated.confidence == "medium"


def test_query_expansions_for_http3() -> None:
    expansions = _query_expansions("Can HTTPX support HTTP/3?")

    assert "HTTP/3" in expansions
    assert "QUIC" in expansions


def test_calibrated_status_from_rationale() -> None:
    status = _calibrated_status(
        [
            ThreadAssessment(
                number=12,
                relevance="direct_decision",
                decision_status="unknown",
                rationale="Maintainer said this is not planned and declined the request.",
            )
        ]
    )

    assert status == "rejected"


def test_calibrated_status_prefers_rejected_over_duplicate() -> None:
    status = _calibrated_status(
        [
            ThreadAssessment(
                number=12,
                relevance="direct_decision",
                decision_status="duplicate",
                rationale="Maintainer declined the request and marked a nearby thread duplicate.",
            )
        ]
    )

    assert status == "rejected"


def test_status_from_result_text_overrides_duplicate() -> None:
    result = PriorDecisionResult(
        prior_decision_found=True,
        direct_decision_found=True,
        adjacent_decision_found=False,
        decision_status="duplicate",
        decision_summary="Maintainer declined this direction.",
        reasoning="The request was not planned.",
        canonical_threads=[12],
        confidence="high",
        suggested_response="See #12.",
    )

    assert _status_from_result_text(result, "duplicate") == "rejected"
