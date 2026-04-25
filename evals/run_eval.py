import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.graph.builder import run_query
from app.rag.indexer import build_index
from app.schemas.repo_answer import RepoAnswer
from app.schemas.triage import IssueTriageResult
from evals.metrics import EvalMetrics

CASES_PATH = Path("evals/cases/cases.jsonl")


def main() -> None:
    build_index(Path("data/fixtures/sample_repo"), "sample/repo")
    cases = _load_cases()
    schema_valid = 0
    triage_total = 0
    category_correct = 0
    severity_correct = 0
    answer_total = 0
    answer_with_evidence = 0
    latencies: list[float] = []

    for case in cases:
        start = time.perf_counter()
        payload = run_query(
            repo_id=case["repo_id"],
            question=case["question"],
            task_type=case["task_type"],
            context=case.get("context", {}),
        )
        latencies.append((time.perf_counter() - start) * 1000)
        result = payload["result"]
        if case["task_type"] == "issue_triage":
            triage_total += 1
            parsed = IssueTriageResult.model_validate(result)
            schema_valid += 1
            category_correct += parsed.issue_category == case["expected_category"]
            severity_correct += parsed.severity == case["expected_severity"]
        else:
            answer_total += 1
            parsed_answer = RepoAnswer.model_validate(result)
            schema_valid += 1
            answer_with_evidence += bool(parsed_answer.evidence)

    metrics = EvalMetrics(
        cases=len(cases),
        schema_valid_rate=100 * schema_valid / len(cases),
        triage_category_accuracy=100 * category_correct / max(1, triage_total),
        severity_accuracy=100 * severity_correct / max(1, triage_total),
        answer_has_evidence_rate=100 * answer_with_evidence / max(1, answer_total),
        average_latency_ms=sum(latencies) / max(1, len(latencies)),
    )
    print(metrics.render())


def _load_cases() -> list[dict]:
    with CASES_PATH.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


if __name__ == "__main__":
    main()
