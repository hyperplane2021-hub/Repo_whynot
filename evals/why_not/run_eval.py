import json
import sys
import time
from pathlib import Path
from typing import Any

import typer

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services.prior_decision_investigator import investigate_prior_decision

CASES_PATH = Path("evals/why_not/cases.jsonl")


def main(runs: int = 1) -> None:
    cases = _load_cases()
    all_runs: list[list[dict[str, Any]]] = []
    for run_index in range(1, runs + 1):
        print(f"\nRun {run_index}/{runs}")
        rows: list[dict[str, Any]] = []
        for case in cases:
            start = time.perf_counter()
            payload = investigate_prior_decision(case["repo"], case["question"])
            latency_ms = (time.perf_counter() - start) * 1000
            result = payload["result"]
            if hasattr(result, "model_dump"):
                result = result.model_dump()
            rows.append(_score_case(case, result, payload, latency_ms))
        all_runs.append(rows)
        _print_report(rows)
    if len(all_runs) > 1:
        _print_multi_run_summary(all_runs)


def _score_case(
    case: dict[str, Any],
    result: dict[str, Any],
    payload: dict[str, Any],
    latency_ms: float,
) -> dict[str, Any]:
    expected = case["expected_threads"]
    predicted = result.get("canonical_threads", [])
    relation = _predicted_relation(result)
    trace = payload.get("investigation_trace", [])
    queries = sum(len(item.get("queries", [])) for item in trace)
    threads = sorted({thread for item in trace for thread in item.get("threads_found", [])})
    return {
        "repo": case["repo"],
        "question": case["question"],
        "expected_threads": expected,
        "predicted_threads": predicted,
        "threads_found": threads,
        "top1_hit": bool(expected) and bool(predicted) and predicted[0] in expected,
        "top3_hit": bool(expected) and any(thread in expected for thread in predicted[:3]),
        "expected_none": not expected,
        "predicted_none": not result.get("prior_decision_found", False),
        "status_ok": result.get("decision_status") == case["expected_status"],
        "relation_ok": relation == case["expected_relation"],
        "predicted_status": result.get("decision_status"),
        "expected_status": case["expected_status"],
        "predicted_relation": relation,
        "expected_relation": case["expected_relation"],
        "false_positive": not expected and result.get("prior_decision_found", False),
        "latency_ms": latency_ms,
        "queries": queries,
        "rounds": len(trace),
    }


def _predicted_relation(result: dict[str, Any]) -> str:
    if result.get("direct_decision_found"):
        return "direct_decision"
    if result.get("adjacent_decision_found"):
        return "adjacent_decision"
    return "none"


def _print_report(rows: list[dict[str, Any]]) -> None:
    cases = len(rows)
    positive = [row for row in rows if not row["expected_none"]]
    negative = [row for row in rows if row["expected_none"]]
    print("RepoOps Why-Not Eval")
    print("--------------------")
    print(f"Cases: {cases}")
    print(f"Positive cases: {len(positive)}")
    print(f"Negative cases: {len(negative)}")
    print(f"Top-1 canonical hit: {_pct(sum(row['top1_hit'] for row in positive), len(positive))}")
    print(f"Top-3 canonical hit: {_pct(sum(row['top3_hit'] for row in positive), len(positive))}")
    print(f"Status accuracy: {_pct(sum(row['status_ok'] for row in rows), cases)}")
    print(f"Relation accuracy: {_pct(sum(row['relation_ok'] for row in rows), cases)}")
    false_positive_count = sum(row["false_positive"] for row in negative)
    predicted_none_count = sum(row["predicted_none"] for row in negative)
    print(f"False positive rate: {_pct(false_positive_count, len(negative))}")
    print(f"Unknown accuracy: {_pct(predicted_none_count, len(negative))}")
    print(f"Average latency: {sum(row['latency_ms'] for row in rows) / cases:.0f} ms")
    print(f"Average queries: {sum(row['queries'] for row in rows) / cases:.1f}")
    print()
    print("Misses:")
    for row in rows:
        if row["expected_none"]:
            bad = row["false_positive"] or not row["relation_ok"] or not row["status_ok"]
        else:
            bad = not row["top3_hit"] or not row["relation_ok"] or not row["status_ok"]
        if bad:
            print(
                "- "
                f"{row['repo']} | {row['question']} | "
                f"expected={row['expected_threads']} predicted={row['predicted_threads']} "
                f"found={row['threads_found']} "
                f"top3={row['top3_hit']} "
                f"status={row['predicted_status']}/{row['expected_status']} "
                f"relation={row['predicted_relation']}/{row['expected_relation']}"
            )


def _print_multi_run_summary(all_runs: list[list[dict[str, Any]]]) -> None:
    summaries = [_summary_metrics(rows) for rows in all_runs]
    print()
    print("Multi-run Summary")
    print("-----------------")
    for key in (
        "top1",
        "top3",
        "status",
        "relation",
        "false_positive",
        "unknown",
        "latency",
    ):
        values = [summary[key] for summary in summaries]
        mean = sum(values) / len(values)
        spread = max(values) - min(values)
        suffix = " ms" if key == "latency" else "%"
        print(f"{key}: mean={mean:.1f}{suffix} range={spread:.1f}{suffix}")


def _summary_metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    positive = [row for row in rows if not row["expected_none"]]
    negative = [row for row in rows if row["expected_none"]]
    cases = len(rows)
    return {
        "top1": _ratio(sum(row["top1_hit"] for row in positive), len(positive)),
        "top3": _ratio(sum(row["top3_hit"] for row in positive), len(positive)),
        "status": _ratio(sum(row["status_ok"] for row in rows), cases),
        "relation": _ratio(sum(row["relation_ok"] for row in rows), cases),
        "false_positive": _ratio(sum(row["false_positive"] for row in negative), len(negative)),
        "unknown": _ratio(sum(row["predicted_none"] for row in negative), len(negative)),
        "latency": sum(row["latency_ms"] for row in rows) / cases,
    }


def _pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{100 * numerator / denominator:.1f}%"


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return 100 * numerator / denominator


def _load_cases() -> list[dict[str, Any]]:
    with CASES_PATH.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


if __name__ == "__main__":
    typer.run(main)
