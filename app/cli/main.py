import json
from pathlib import Path
from typing import Annotated

import typer

from app.github.ingest import GitHubIngestError, ingest_github_issues
from app.graph.builder import run_query
from app.rag.indexer import build_index
from app.services.prior_decision_investigator import investigate_prior_decision
from app.services.prior_decisions import detect_prior_decision

app = typer.Typer(help="Repo_whynot v0.3")
eval_app = typer.Typer(help="Run local evals.")
github_app = typer.Typer(help="Read-only GitHub ingest commands.")
app.add_typer(eval_app, name="eval")
app.add_typer(github_app, name="github")


@app.command()
def index(
    repo_path: Annotated[Path, typer.Option("--repo-path", exists=True, file_okay=False)],
    repo_id: Annotated[str, typer.Option("--repo-id")],
) -> None:
    stats = build_index(repo_path, repo_id)
    typer.echo(f"Indexed repo: {stats.repo_id}")
    typer.echo(f"Docs chunks: {stats.docs_chunks}")
    typer.echo(f"Code chunks: {stats.code_chunks}")
    typer.echo(f"History chunks: {stats.history_chunks}")
    typer.echo(f"Index path: {stats.index_path}")


@app.command()
def ask(
    repo_id: Annotated[str, typer.Option("--repo-id")],
    question: Annotated[str, typer.Option("--question")],
) -> None:
    payload = run_query(repo_id=repo_id, question=question, task_type="repo_qa")
    typer.echo(json.dumps(payload["result"], ensure_ascii=False, indent=2))


@app.command()
def triage(
    repo_id: Annotated[str, typer.Option("--repo-id")],
    issue_file: Annotated[Path, typer.Option("--issue-file", exists=True, dir_okay=False)],
    title: Annotated[str | None, typer.Option("--title")] = None,
) -> None:
    body = issue_file.read_text(encoding="utf-8")
    issue_title = title or _title_from_markdown(body) or issue_file.stem.replace("_", " ")
    payload = run_query(
        repo_id=repo_id,
        question=issue_title,
        task_type="issue_triage",
        context={"issue_title": issue_title, "issue_body": body},
    )
    typer.echo(json.dumps(payload["result"], ensure_ascii=False, indent=2))


@app.command("why-not")
def why_not(
    repo: Annotated[str, typer.Option("--repo")],
    question: Annotated[str, typer.Option("--question")],
    limit: Annotated[int, typer.Option("--limit")] = 8,
    investigate: Annotated[bool, typer.Option("--investigate")] = False,
) -> None:
    if investigate:
        payload = investigate_prior_decision(repo=repo, question=question)
        if hasattr(payload["result"], "model_dump"):
            payload["result"] = payload["result"].model_dump()
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        result = detect_prior_decision(repo=repo, question=question, k=limit)
        typer.echo(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))


@github_app.command("ingest")
def github_ingest(
    repo: Annotated[str, typer.Option("--repo")],
    limit: Annotated[int, typer.Option("--limit")] = 100,
    query: Annotated[str | None, typer.Option("--query")] = None,
) -> None:
    try:
        result = ingest_github_issues(repo=repo, limit=limit, query=query)
    except GitHubIngestError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@eval_app.command("run")
def eval_run() -> None:
    from evals.run_eval import main

    main()


def _title_from_markdown(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return None


if __name__ == "__main__":
    app()
