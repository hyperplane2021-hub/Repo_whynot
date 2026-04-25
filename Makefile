.PHONY: test lint index eval api

test:
	uv run pytest

lint:
	uv run ruff check .

index:
	uv run repoops index --repo-path ./data/fixtures/sample_repo --repo-id sample/repo

eval:
	uv run python evals/run_eval.py

api:
	uv run uvicorn app.main:app --reload

