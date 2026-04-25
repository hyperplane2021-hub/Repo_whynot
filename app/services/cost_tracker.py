from dataclasses import dataclass


@dataclass
class CostTracker:
    llm_calls: int = 0
    max_llm_calls: int = 4

    def record_llm_call(self) -> None:
        if self.llm_calls >= self.max_llm_calls:
            raise RuntimeError("LLM call budget exceeded")
        self.llm_calls += 1

