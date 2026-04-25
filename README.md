# Repo_whynot

![Repo_whynot](assets/repoops-why-not.svg)

Repo_whynot is a small read-only tool for answering "why not?" questions from repository
history. It searches prior GitHub issues, finds maintainer decisions, and returns cited
evidence before you open a new issue or PR.

## What It Does

Repo_whynot helps answer questions like:

- "Why not use argparse internally?"
- "Can this project support HTML output?"
- "Was this feature already rejected?"
- "Is there an old issue that explains the maintainer position?"

It searches closed GitHub issues, grades candidate threads, and returns a structured
`PriorDecisionResult` with cited thread numbers, confidence, status, facts, inferences,
and uncertainties.

## Why This Exists

Many project decisions live in old issues rather than docs. Repo_whynot is useful when a
contributor or maintainer wants quick context on whether an idea has already been accepted,
rejected, deferred, or discussed as a duplicate.

## Safety Model

- Read-only GitHub issue search.
- No comments, labels, closes, pushes, or GitHub mutations.
- No arbitrary shell tool in the workflow.
- Tool loops are capped and configurable.
- All LLM nodes have deterministic fallback behavior.
- Final answers distinguish supported facts, inferences, and uncertainties.

## Quick Start

```bash
uv sync
cp .env.example .env
```

For deterministic local behavior without API calls, keep:

```text
REPOOPS_MODEL_PROVIDER=none
REPOOPS_ENABLE_LLM_SYNTHESIS=false
```

To enable LLM-assisted planning and synthesis:

```text
REPOOPS_MODEL_PROVIDER=openai
REPOOPS_MODEL_NAME=gpt-5.4-mini
REPOOPS_OPENAI_API_KEY=...
REPOOPS_ENABLE_LLM_SYNTHESIS=true
```

For GitHub search:

```text
REPOOPS_GITHUB_TOKEN=...
```

## Try The Why-Not Investigator

```bash
uv run repoops why-not \
  --repo pallets/click \
  --question "Why not use argparse internally?" \
  --investigate
```

You can also ingest closed issues into a local JSONL cache:

```bash
uv run repoops github ingest --repo pallets/click --limit 100
uv run repoops why-not --repo pallets/click --question "Why not use argparse internally?"
```

## Compare Against Naive GitHub Search

```bash
uv run python evals/why_not/compare_search.py
```

Current seed benchmark:

```text
Cases: 9
Baseline top-1: 33.3% (2/6)
Baseline top-3: 50.0% (3/6)
Repo_whynot top-1: 100.0% (6/6)
Repo_whynot top-3: 100.0% (6/6)
Baseline unknown accuracy: 100.0% (3/3)
Repo_whynot unknown accuracy: 100.0% (3/3)
```

This is a small eval, not a broad claim. It is useful because it tests the product thesis:
query planning and evidence grading can recover prior decisions that plain issue search
misses.

## API

```bash
uv run uvicorn app.main:app --reload
```

```bash
curl http://127.0.0.1:8000/health
```

## Development

```bash
uv run ruff check .
uv run pytest
```

Project-generated caches live under `data/indexes/` and `data/github/` and are ignored by
git, except for placeholder files and sample fixtures.
