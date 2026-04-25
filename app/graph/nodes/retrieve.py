from app.graph.state import GraphState
from app.rag.indexer import load_index
from app.rag.retrievers import retrieve_code, retrieve_docs, retrieve_history
from app.rag.types import IndexDocument, RetrievalResult


def retrieve(state: GraphState) -> GraphState:
    if state.query_plan:
        docs_queries = state.query_plan.docs_queries or [state.question]
        code_queries = state.query_plan.code_queries or [state.question]
        history_queries = state.query_plan.history_queries or [state.question]
    else:
        queries = state.rewritten_queries
        docs_queries = [queries.get("docs", state.question)]
        code_queries = [queries.get("code", state.question)]
        history_queries = [queries.get("history", state.question)]

    results = []
    for query in docs_queries:
        results.extend(retrieve_docs(state.repo_id, query, k=5))
    for query in code_queries:
        results.extend(retrieve_code(state.repo_id, query, k=5))
    for query in history_queries:
        results.extend(retrieve_history(state.repo_id, query, k=5))
    results.extend(_preferred_evidence_results(state))
    state.retrieval_results = _rank_with_plan_preferences(_dedupe_results(results), state)
    state.node_metadata["retrieve"] = {"retrieval_results": len(state.retrieval_results)}
    return state


def _dedupe_results(results: list[RetrievalResult]) -> list[RetrievalResult]:
    by_id = {}
    for result in results:
        existing = by_id.get(result.document.id)
        if existing is None or result.score > existing.score:
            by_id[result.document.id] = result
    return sorted(by_id.values(), key=lambda item: item.score, reverse=True)


def _rank_with_plan_preferences(
    results: list[RetrievalResult],
    state: GraphState,
) -> list[RetrievalResult]:
    if not state.query_plan:
        return results
    preferred = [item.lower() for item in state.query_plan.preferred_evidence]
    avoid = [item.lower() for item in state.query_plan.avoid_evidence]
    ranked: list[RetrievalResult] = []
    for result in results:
        path = str(result.document.metadata.get("path", "")).lower()
        text = f"{path} {result.document.text[:500]}".lower()
        score = result.score
        score *= _intent_source_weight(state.query_plan.intent_family, result.document.source_type)
        score *= _preference_multiplier(text, path, preferred, avoid)
        ranked.append(RetrievalResult(document=result.document, score=round(score, 4)))
    return sorted(ranked, key=lambda item: item.score, reverse=True)


def _intent_source_weight(intent_family: str, source_type: str) -> float:
    if intent_family == "overview":
        if source_type == "doc":
            return 1.35
        if source_type == "code":
            return 0.95
        return 0.5
    if intent_family in {"how_it_works", "where_is"} and source_type == "code":
        return 1.25
    if intent_family == "issue_triage" and source_type == "issue":
        return 1.35
    return 1.0


def _preference_multiplier(
    text: str,
    path: str,
    preferred: list[str],
    avoid: list[str],
) -> float:
    multiplier = 1.0
    for preference in preferred:
        if _preference_matches(preference, text, path):
            multiplier += 0.25
    for preference in avoid:
        if _preference_matches(preference, text, path):
            multiplier -= 0.25
    return max(0.25, min(2.0, multiplier))


def _preference_matches(preference: str, text: str, path: str) -> bool:
    aliases = {
        "readme": ["readme"],
        "project metadata": ["pyproject.toml", "package.json", "setup.py", "setup.cfg"],
        "docs index": ["docs/index", "index.md", "index.rst"],
        "quickstart": ["quickstart"],
        "public api modules": ["__init__.py", "_api.py", "api.py"],
        "contributing guide": ["contributing"],
        "changelog": ["changelog", "changes"],
        "tests": ["tests/"],
    }
    needles = aliases.get(preference, [preference])
    return any(needle in path or needle in text for needle in needles)


def _preferred_evidence_results(state: GraphState) -> list[RetrievalResult]:
    if not state.query_plan or not state.query_plan.preferred_evidence:
        return []
    documents = load_index(state.repo_id)
    preferred = [item.lower() for item in state.query_plan.preferred_evidence]
    results: list[RetrievalResult] = []
    for document in documents:
        path = str(document.metadata.get("path", "")).lower()
        text = f"{path} {document.text[:500]}".lower()
        if any(_preference_matches(preference, text, path) for preference in preferred):
            results.append(RetrievalResult(document=document, score=_preferred_score(document)))
    return results


def _preferred_score(document: IndexDocument) -> float:
    path = str(document.metadata.get("path", "")).lower()
    if "readme" in path:
        return 50.0
    if path in {"pyproject.toml", "package.json", "setup.py", "setup.cfg"}:
        return 48.0
    if "docs/index" in path:
        return 45.0
    if "quickstart" in path:
        return 42.0
    return 30.0
