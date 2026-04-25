import json

from app.config import project_root
from app.services.prior_decisions import detect_prior_decision


def test_prior_decision_fallback_from_ingested_issues() -> None:
    repo = "local/test-prior"
    data_dir = project_root() / "data" / "github" / "local_test-prior"
    data_dir.mkdir(parents=True, exist_ok=True)
    issue = {
        "number": 42,
        "title": "Do not switch to argparse",
        "body": (
            "This proposal was discussed and rejected because Click needs nested "
            "command contexts."
        ),
        "state": "closed",
        "labels": ["feature", "wontfix"],
        "url": "https://example.test/issues/42",
        "comments_sample": [
            {
                "author": "maintainer",
                "body": "We won't fix this because custom parsing is core to Click.",
            }
        ],
    }
    (data_dir / "issues.jsonl").write_text(json.dumps(issue) + "\n", encoding="utf-8")

    result = detect_prior_decision(repo, "Why not use argparse?", k=3)

    assert result.prior_decision_found is True
    assert result.decision_status == "rejected"
    assert result.canonical_threads == [42]
    assert result.evidence[0].number == 42


def test_prior_decision_no_candidates() -> None:
    repo = "local/test-empty"
    data_dir = project_root() / "data" / "github" / "local_test-empty"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "issues.jsonl").write_text("", encoding="utf-8")

    result = detect_prior_decision(repo, "Why not support HTML output?", k=3)

    assert result.prior_decision_found is False
    assert result.decision_status == "unknown"
    assert result.confidence == "low"
