from app.graph.state import GraphState
from app.rag.retrievers import tokenize
from app.schemas.planning import QueryPlan
from app.services.model_router import generate_json_result


def query_rewrite(state: GraphState) -> GraphState:
    fallback_plan = _fallback_query_plan(state)
    llm_result = generate_json_result(
        instructions=(
            "You are the Repo_whynot LLM Query Planner. Return only valid JSON matching "
            "QueryPlan. Set intent_family to one of overview, how_it_works, where_is, "
            "troubleshooting, change_impact, issue_triage, usage, or unknown. Use "
            "intent_description, preferred_evidence, and avoid_evidence to describe the "
            "retrieval strategy without hard-coding user language. Do not plan tool calls."
        ),
        payload={
            "request_id": state.request_id,
            "task_type": state.task_type,
            "question": state.question,
            "context": state.context,
            "fallback_plan": fallback_plan.model_dump(),
        },
        fallback=fallback_plan.model_dump(),
        schema=QueryPlan,
    )
    plan = QueryPlan.model_validate(llm_result.data)
    state.query_plan = plan
    state.node_fallbacks["query_rewrite"] = llm_result.fallback_used
    state.node_models["query_rewrite"] = llm_result.model_used
    state.node_metadata["query_rewrite"] = {
        "docs_queries": len(plan.docs_queries),
        "code_queries": len(plan.code_queries),
        "history_queries": len(plan.history_queries),
        "keywords": plan.keywords,
    }
    state.rewritten_queries = {
        "docs": " ".join(plan.docs_queries),
        "code": " ".join(plan.code_queries),
        "history": " ".join(plan.history_queries),
    }
    return state


def _fallback_query_plan(state: GraphState) -> QueryPlan:
    issue_text = " ".join(
        [
            state.question,
            str(state.context.get("issue_title", "")),
            str(state.context.get("issue_body", "")),
        ]
    ).strip()
    query = issue_text or state.question
    keywords = tokenize(query)[:12]
    likely_files = _likely_files(query)
    likely_modules = sorted({path.split("/")[1] for path in likely_files if "/" in path})
    intent_family = _fallback_intent_family(query, state.task_type)
    preferred, avoid = _fallback_evidence_preferences(intent_family)
    return QueryPlan(
        intent_family=intent_family,
        intent_description=f"Rule-based fallback plan for {intent_family}.",
        docs_queries=[query],
        code_queries=[query, *likely_files],
        history_queries=[query],
        preferred_evidence=preferred,
        avoid_evidence=avoid,
        likely_modules=likely_modules,
        likely_files=likely_files,
        keywords=keywords,
        search_strategy="keyword_overlap_with_source_lanes",
    )


def _likely_files(text: str) -> list[str]:
    lowered = text.lower()
    files: list[str] = []
    if any(word in lowered for word in ("auth", "token", "login", "session", "认证")):
        files.append("src/auth/session.py")
    if "api" in lowered or "route" in lowered:
        files.append("src/api/routes.py")
    if any(word in lowered for word in ("doc", "docs", "documentation", "文档")):
        files.append("docs/authentication.md")
    return files


def _fallback_intent_family(text: str, task_type: str) -> str:
    lowered = text.lower()
    if task_type == "issue_triage":
        return "issue_triage"
    if any(word in lowered for word in ("overview", "purpose", "what is", "what does")):
        return "overview"
    if any(word in lowered for word in ("在哪里", "where", "which file")):
        return "where_is"
    if any(word in lowered for word in ("how", "怎么", "如何", "works", "implement")):
        return "how_it_works"
    return "unknown"


def _fallback_evidence_preferences(intent_family: str) -> tuple[list[str], list[str]]:
    if intent_family == "overview":
        return (
            ["README", "project metadata", "docs index", "quickstart", "public API modules"],
            ["contributing guide", "changelog", "tests"],
        )
    if intent_family == "usage":
        return (["README", "quickstart", "examples", "docs"], ["changelog"])
    if intent_family == "issue_triage":
        return (["related issues", "source files", "error docs"], ["unrelated examples"])
    return (["docs", "source files"], ["unrelated tests"])
