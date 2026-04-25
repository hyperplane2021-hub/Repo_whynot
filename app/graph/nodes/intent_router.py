from app.graph.state import GraphState

TRIAGE_HINTS = ("issue", "bug", "error", "fails", "失败", "报错", "分诊", "重复")


def intent_router(state: GraphState) -> GraphState:
    if state.task_type in {"issue_triage", "repo_qa"}:
        return state
    text = " ".join(
        [
            state.question,
            str(state.context.get("issue_title", "")),
            str(state.context.get("issue_body", "")),
        ]
    ).lower()
    state.task_type = "issue_triage" if any(hint in text for hint in TRIAGE_HINTS) else "repo_qa"
    return state

