from pathlib import Path
from typing import Any

from app.config import get_settings
from app.graph.state import GraphState
from app.rag.indexer import load_manifest
from app.tools.read_only import git_log, grep_repo, read_file, search_issues
from app.tools.validation import resolve_repo_path

ALLOWED_TOOLS = {"read_file", "grep_repo", "git_log", "search_issues"}


def tool_loop(state: GraphState) -> GraphState:
    manifest = load_manifest(state.repo_id)
    repo_root = Path(manifest["repo_path"])
    results: list[dict[str, Any]] = []
    settings = get_settings()
    calls = _validated_calls(repo_root, state.planned_tools)
    cursor = 0
    for round_index in range(settings.max_tool_rounds):
        round_calls = calls[cursor : cursor + settings.max_tool_calls_per_round]
        if not round_calls:
            break
        cursor += len(round_calls)
        for call in round_calls:
            try:
                results.append(
                    {
                        "round": round_index + 1,
                        "name": call["name"],
                        "reason": call.get("reason", ""),
                        "evidence_ids": call.get("evidence_ids", []),
                        "result": _run_tool(repo_root, call),
                    }
                )
            except Exception as exc:  # Keep tool failures non-fatal for the workflow.
                results.append(
                    {
                        "round": round_index + 1,
                        "name": call.get("name", "unknown"),
                        "error": str(exc),
                    }
                )
    state.tool_results = results
    state.node_metadata["tool_loop"] = {
        "validated_calls": len(calls),
        "executed_calls": len(results),
        "max_tool_rounds": settings.max_tool_rounds,
        "max_tool_calls_per_round": settings.max_tool_calls_per_round,
    }
    return state


def _run_tool(repo_root: Path, call: dict[str, Any]) -> Any:
    name = call["name"]
    args = call.get("args", {})
    if name == "read_file":
        return read_file(repo_root, args["path"])
    if name == "grep_repo":
        return grep_repo(repo_root, args["query"], args.get("path_glob"), args.get("limit", 20))
    if name == "git_log":
        return git_log(repo_root, args.get("paths"), args.get("limit", 20))
    if name == "search_issues":
        return search_issues(repo_root, args["query"], args.get("state"), args.get("limit", 10))
    raise ValueError(f"Unsupported tool: {name}")


def _validated_calls(repo_root: Path, calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    valid: list[dict[str, Any]] = []
    for call in calls:
        if call.get("name") not in ALLOWED_TOOLS:
            continue
        args = call.get("args", {})
        try:
            if call["name"] == "read_file":
                resolve_repo_path(repo_root, args["path"])
            elif call["name"] == "git_log":
                for path in args.get("paths") or []:
                    resolve_repo_path(repo_root, path)
            elif call["name"] in {"grep_repo", "search_issues"}:
                if not isinstance(args.get("query"), str) or not args["query"].strip():
                    continue
        except Exception:
            continue
        valid.append(call)
    return valid
