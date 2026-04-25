# Demo

```bash
uv run repoops index --repo-path ./data/fixtures/sample_repo --repo-id sample/repo
uv run repoops ask --repo-id sample/repo --question "认证模块怎么处理 token？"
uv run repoops triage --repo-id sample/repo --issue-file ./data/samples/issue_auth_bug.md
uv run python evals/run_eval.py
```

All commands use the checked-in sample repository and local JSON indexes. With
`REPOOPS_ENABLE_LLM_SYNTHESIS=true`, v0.2 uses the configured model for query planning,
evidence grading, tool planning, and final synthesis. With it disabled, the same graph runs
through deterministic fallbacks.

## Prior Decision Demo

```bash
uv run repoops github ingest --repo pallets/click --limit 50
uv run repoops why-not --repo pallets/click --question "Why not use argparse internally?"
```
