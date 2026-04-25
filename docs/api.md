# API

## `GET /health`

Returns service status and version.

## `POST /index`

Builds a local JSONL index.

```json
{
  "repo_id": "sample/repo",
  "repo_path": "./data/fixtures/sample_repo"
}
```

## `POST /query`

Runs issue triage or repo QA.

```json
{
  "repo_id": "sample/repo",
  "task_type": "auto",
  "question": "Login fails after token expires",
  "context": {
    "issue_title": "Login fails after token expires",
    "issue_body": "Users are logged out when refresh token expires."
  }
}
```

The response includes `request_id`, `task_type`, `result`, and `trace`. `result.evidence`
items include stable `evidence_id` values. Final synthesis also separates supported facts,
inferences, and uncertainties.
