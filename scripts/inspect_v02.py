from pathlib import Path

from app.graph.builder import run_query
from app.rag.indexer import build_index

CASES = [
    {
        "name": "qa_auth_refresh",
        "task_type": "repo_qa",
        "question": "How does authentication handle token refresh?",
        "context": {},
    },
    {
        "name": "triage_duplicate_auth_bug",
        "task_type": "issue_triage",
        "question": "Login fails after token expires",
        "context": {
            "issue_title": "Login fails after token expires",
            "issue_body": "Users are logged out when refresh token expires after idle sessions.",
        },
    },
    {
        "name": "triage_docs_request",
        "task_type": "issue_triage",
        "question": "Document refresh token lifecycle",
        "context": {
            "issue_title": "Document refresh token lifecycle",
            "issue_body": "Docs should explain why users must sign in again after idle sessions.",
        },
    },
    {
        "name": "qa_unknown_area",
        "task_type": "repo_qa",
        "question": "Does this repository support billing invoices?",
        "context": {},
    },
]


def main() -> None:
    build_index(Path("data/fixtures/sample_repo"), "sample/repo")
    for case in CASES:
        print(f"\n=== {case['name']} ===")
        payload = run_query(
            repo_id="sample/repo",
            question=case["question"],
            task_type=case["task_type"],
            context=case["context"],
        )
        result = payload["result"]
        print(f"request_id: {payload['request_id']}")
        print(f"task_type: {payload['task_type']}")
        if "answer" in result:
            print(f"answer: {result['answer']}")
        else:
            print(f"category: {result['issue_category']}")
            print(f"severity: {result['severity']}")
            print(f"duplicate_likelihood: {result['duplicate_likelihood']}")
            print(f"next_action: {result['recommended_next_action']}")

        print("supported_facts:")
        for fact in result.get("supported_facts", [])[:3]:
            print(f"  - {fact['text']} [{', '.join(fact['evidence_ids'])}]")

        print("uncertainties:")
        for uncertainty in result.get("uncertainties", [])[:3]:
            print(f"  - {uncertainty['text']}")

        print("evidence:")
        for item in result.get("evidence", [])[:5]:
            label = item.get("title") or item.get("path") or item.get("source_type")
            print(
                "  - "
                f"{item.get('evidence_id')} {item.get('source_type')} "
                f"{item.get('relevance_grade')}/{item.get('role')} {label}"
            )

        print("trace:")
        for trace in payload["trace"]:
            model = trace["model_used"] or "local"
            fallback = "fallback" if trace["fallback_used"] else "ok"
            print(f"  - {trace['node_name']}: {model} {fallback} {trace['latency_ms']:.0f}ms")


if __name__ == "__main__":
    main()
