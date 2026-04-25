from app.services.prior_decision_investigator import investigate_prior_decision

CASES = [
    {
        "repo": "Textualize/rich",
        "question": "Can Rich support HTML output?",
    },
    {
        "repo": "Textualize/rich",
        "question": "Why not support a strict plain text mode in Jupyter?",
    },
    {
        "repo": "Textualize/rich",
        "question": "Can Rich disable hyperlinks in notebook output?",
    },
    {
        "repo": "pallets/click",
        "question": "Why not use argparse internally?",
    },
    {
        "repo": "pallets/click",
        "question": "Can Click support long command lines from a file like argparse?",
    },
    {
        "repo": "pallets/click",
        "question": "Why not parse function signatures automatically?",
    },
    {
        "repo": "encode/httpx",
        "question": "Can HTTPX support requests-style hooks for all events?",
    },
    {
        "repo": "encode/httpx",
        "question": "Why not support urllib3 retries directly?",
    },
    {
        "repo": "encode/httpx",
        "question": "Can HTTPX support HTTP/3?",
    },
]


def main() -> None:
    for index, case in enumerate(CASES, start=1):
        print(f"\n=== {index}. {case['repo']} ===")
        print(f"Q: {case['question']}")
        payload = investigate_prior_decision(case["repo"], case["question"])
        result = payload["result"]
        if hasattr(result, "model_dump"):
            result = result.model_dump()
        print(
            "decision: "
            f"found={result['prior_decision_found']} "
            f"status={result['decision_status']} "
            f"confidence={result['confidence']} "
            f"threads={result['canonical_threads']}"
        )
        print(f"summary: {result['decision_summary']}")
        if result.get("uncertainties"):
            print(f"uncertainty: {result['uncertainties'][0]['text']}")
        print("trace:")
        for trace in payload.get("investigation_trace", []):
            print(
                f"  round {trace['round']}: "
                f"queries={len(trace['queries'])} "
                f"threads={trace['threads_found']} "
                f"next={trace['next_action']}"
            )
            direct = [
                item["number"]
                for item in trace.get("assessments", [])
                if item["relevance"] == "direct_decision"
            ]
            adjacent = [
                item["number"]
                for item in trace.get("assessments", [])
                if item["relevance"] == "adjacent_decision"
            ]
            print(f"    direct={direct} adjacent={adjacent}")


if __name__ == "__main__":
    main()
