# Architecture

Repo_whynot v0.2 uses an explicit graph runtime:

```text
intent_router -> query_rewrite -> retrieve -> evidence_merge
  -> evidence_grader -> tool_planner -> tool_loop
  -> synthesize_output -> action_gate
```

Retrieval is split into three source lanes:

- docs: README and Markdown files;
- code: Python, TypeScript, JavaScript, Go, and Rust files;
- history: local issues, PRs, and commits stored as JSONL fixtures.

The graph returns one of two schemas:

- `IssueTriageResult`
- `RepoAnswer`

LLM involvement is intentionally scoped:

- Query planner: produces a structured `QueryPlan`.
- Evidence grader: grades candidate evidence and assigns evidence roles.
- Tool planner: proposes read-only tool calls only.
- Final synthesis: produces schema-valid grounded output with `evidence_id` citations.

The model never executes tools. Tool execution stays in the controlled `tool_loop`, where
all calls are validated against the allowlist and repository path guard.

Every LLM node has deterministic fallback behavior. The graph continues with rule-based
defaults if model calls fail or return invalid JSON.

Each request carries a `request_id`, and every node appends trace data:

- node name;
- model used;
- latency;
- input and output evidence counts;
- fallback status.
