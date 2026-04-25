import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.github.ingest import search_github_issues
from app.services.prior_decision_investigator import investigate_prior_decision

CASES_PATH = Path("evals/why_not/cases.jsonl")


def main() -> None:
    cases = _load_cases()
    rows = [_score_case(case) for case in cases]
    _print_report(rows)


def _score_case(case: dict[str, Any]) -> dict[str, Any]:
    expected = case["expected_threads"]
    baseline_threads = [
        item["number"] for item in search_github_issues(case["repo"], case["question"], limit=10)
    ]
    payload = investigate_prior_decision(case["repo"], case["question"])
    result = payload["result"]
    if hasattr(result, "model_dump"):
        result = result.model_dump()
    repoops_threads = result.get("canonical_threads", [])
    has_expected = bool(expected)
    baseline_top1 = has_expected and bool(baseline_threads) and baseline_threads[0] in expected
    baseline_top3 = has_expected and any(
        thread in expected for thread in baseline_threads[:3]
    )
    repoops_top1 = has_expected and bool(repoops_threads) and repoops_threads[0] in expected
    repoops_top3 = has_expected and any(thread in expected for thread in repoops_threads[:3])
    return {
        "repo": case["repo"],
        "question": case["question"],
        "expected": expected,
        "baseline_threads": baseline_threads,
        "repoops_threads": repoops_threads,
        "baseline_top1": baseline_top1,
        "baseline_top3": baseline_top3,
        "repoops_top1": repoops_top1,
        "repoops_top3": repoops_top3,
        "expected_none": not expected,
        "baseline_none": not baseline_threads,
        "repoops_none": not result.get("prior_decision_found", False),
        "repoops_status": result.get("decision_status"),
        "repoops_relation": _relation(result),
    }


def _relation(result: dict[str, Any]) -> str:
    if result.get("direct_decision_found"):
        return "direct_decision"
    if result.get("adjacent_decision_found"):
        return "adjacent_decision"
    return "none"


def _print_report(rows: list[dict[str, Any]]) -> None:
    positives = [row for row in rows if not row["expected_none"]]
    negatives = [row for row in rows if row["expected_none"]]
    baseline_top1 = sum(row["baseline_top1"] for row in positives)
    baseline_top3 = sum(row["baseline_top3"] for row in positives)
    repoops_top1 = sum(row["repoops_top1"] for row in positives)
    repoops_top3 = sum(row["repoops_top3"] for row in positives)
    baseline_unknown = sum(row["baseline_none"] for row in negatives)
    repoops_unknown = sum(row["repoops_none"] for row in negatives)
    print("Why-Not: Simple GitHub Search vs RepoOps")
    print("----------------------------------------")
    print(f"Cases: {len(rows)}")
    print(
        f"Baseline top-1: {_pct(baseline_top1, len(positives))} "
        f"({baseline_top1}/{len(positives)})"
    )
    print(
        f"Baseline top-3: {_pct(baseline_top3, len(positives))} "
        f"({baseline_top3}/{len(positives)})"
    )
    print(f"RepoOps top-1: {_pct(repoops_top1, len(positives))} ({repoops_top1}/{len(positives)})")
    print(f"RepoOps top-3: {_pct(repoops_top3, len(positives))} ({repoops_top3}/{len(positives)})")
    print(
        "Baseline unknown accuracy: "
        f"{_pct(baseline_unknown, len(negatives))} ({baseline_unknown}/{len(negatives)})"
    )
    print(
        "RepoOps unknown accuracy: "
        f"{_pct(repoops_unknown, len(negatives))} ({repoops_unknown}/{len(negatives)})"
    )
    print()
    print("Details:")
    for row in rows:
        print(
            "- "
            f"{row['repo']} | {row['question']} | expected={row['expected']} | "
            f"baseline={row['baseline_threads'][:3]} | repoops={row['repoops_threads'][:3]} | "
            f"status={row['repoops_status']} relation={row['repoops_relation']}"
        )


def _pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{100 * numerator / denominator:.1f}%"


def _load_cases() -> list[dict[str, Any]]:
    with CASES_PATH.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


if __name__ == "__main__":
    main()
