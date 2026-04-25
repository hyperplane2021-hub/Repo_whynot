from app.graph.state import GraphState
from app.schemas.planning import PlannedToolCall, ToolPlan
from app.services.model_router import generate_json_result

ALLOWED_TOOLS = {"read_file", "grep_repo", "git_log", "search_issues"}


def tool_planner(state: GraphState) -> GraphState:
    fallback_plan = _fallback_tool_plan(state)
    llm_result = generate_json_result(
        instructions=(
            "You are the Repo_whynot LLM Tool Planner. Return only valid JSON matching "
            "ToolPlan. You may plan read-only tool calls only. Allowed tools are "
            "read_file, grep_repo, git_log, search_issues. Do not execute tools and "
            "do not propose write actions."
        ),
        payload={
            "request_id": state.request_id,
            "task_type": state.task_type,
            "question": state.question,
            "query_plan": state.query_plan.model_dump() if state.query_plan else None,
            "evidence": [item.model_dump() for item in state.evidence],
            "evidence_grade_report": (
                state.evidence_grade_report.model_dump() if state.evidence_grade_report else None
            ),
            "fallback_plan": fallback_plan.model_dump(),
        },
        fallback=fallback_plan.model_dump(),
        schema=ToolPlan,
    )
    plan = ToolPlan.model_validate(llm_result.data)
    valid_calls = [_call_to_legacy(call) for call in plan.calls if _is_valid_call(call, state)]
    state.planned_tools = valid_calls
    state.node_fallbacks["tool_planner"] = llm_result.fallback_used
    state.node_models["tool_planner"] = llm_result.model_used
    state.node_metadata["tool_planner"] = {
        "planned_calls": len(plan.calls),
        "valid_calls": len(valid_calls),
    }
    return state


def _fallback_tool_plan(state: GraphState) -> ToolPlan:
    planned: list[PlannedToolCall] = []
    paths = [item.path for item in state.evidence if item.path]
    if paths:
        first_evidence_id = state.evidence[0].evidence_id if state.evidence else None
        planned.append(
            PlannedToolCall(
                tool_name="read_file",
                arguments={"path": paths[0]},
                reason="Inspect the top ranked file evidence.",
                evidence_ids=[first_evidence_id] if first_evidence_id else [],
            )
        )

    text = f"{state.question} {state.context}".lower()
    if any(word in text for word in ("以前", "历史", "commit", "previous", "duplicate")):
        planned.append(
            PlannedToolCall(
                tool_name="git_log",
                arguments={"paths": paths[:1] or None, "limit": 5},
                reason="Check recent commit history for related changes.",
            )
        )
    error_hints = ("error", "fails", "报错", "失败")
    if state.task_type == "issue_triage" and any(word in text for word in error_hints):
        planned.append(
            PlannedToolCall(
                tool_name="grep_repo",
                arguments={"query": state.question or text, "limit": 5},
                reason="Search repository text for reported error terms.",
            )
        )
    if state.task_type == "issue_triage":
        planned.append(
            PlannedToolCall(
                tool_name="search_issues",
                arguments={"query": state.question or text, "limit": 5},
                reason="Find possible duplicates in local issue history.",
            )
        )
    return ToolPlan(calls=planned[:6], rationale="Rule-based read-only tool plan.")


def _is_valid_call(call: PlannedToolCall, state: GraphState) -> bool:
    if call.tool_name not in ALLOWED_TOOLS:
        return False
    args = call.arguments
    evidence_paths = {item.path for item in state.evidence if item.path}
    likely_files = set(state.query_plan.likely_files if state.query_plan else [])
    allowed_paths = evidence_paths | likely_files
    if call.tool_name == "read_file":
        return isinstance(args.get("path"), str) and args["path"] in allowed_paths
    if call.tool_name == "grep_repo":
        return isinstance(args.get("query"), str) and bool(args["query"].strip())
    if call.tool_name == "git_log":
        paths = args.get("paths")
        return paths is None or (
            isinstance(paths, list)
            and all(isinstance(path, str) and path in allowed_paths for path in paths)
        )
    if call.tool_name == "search_issues":
        return isinstance(args.get("query"), str) and bool(args["query"].strip())
    return False


def _call_to_legacy(call: PlannedToolCall) -> dict:
    return {
        "name": call.tool_name,
        "args": call.arguments,
        "reason": call.reason,
        "evidence_ids": call.evidence_ids,
    }
