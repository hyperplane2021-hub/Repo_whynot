from dataclasses import dataclass


@dataclass
class EvalMetrics:
    cases: int
    schema_valid_rate: float
    triage_category_accuracy: float
    severity_accuracy: float
    answer_has_evidence_rate: float
    average_latency_ms: float

    def render(self) -> str:
        return "\n".join(
            [
                "Repo_whynot v0.3 Eval",
                "-----------------",
                f"Cases: {self.cases}",
                f"Schema valid rate: {self.schema_valid_rate:.1f}%",
                f"Triage category accuracy: {self.triage_category_accuracy:.1f}%",
                f"Severity accuracy: {self.severity_accuracy:.1f}%",
                f"Answer has evidence rate: {self.answer_has_evidence_rate:.1f}%",
                f"Average latency: {self.average_latency_ms:.0f} ms",
            ]
        )
