import logging
import time

from app.graph.nodes.action_gate import action_gate
from app.graph.nodes.evidence_grader import evidence_grader
from app.graph.nodes.evidence_merge import evidence_merge
from app.graph.nodes.intent_router import intent_router
from app.graph.nodes.query_rewrite import query_rewrite
from app.graph.nodes.retrieve import retrieve
from app.graph.nodes.synthesize import synthesize_output
from app.graph.nodes.tool_loop import tool_loop
from app.graph.nodes.tool_planner import tool_planner
from app.graph.state import GraphState
from app.schemas.common import NodeTrace

logger = logging.getLogger(__name__)


def run_graph(state: GraphState) -> GraphState:
    for node in (
        intent_router,
        query_rewrite,
        retrieve,
        evidence_merge,
        evidence_grader,
        tool_planner,
        tool_loop,
        synthesize_output,
        action_gate,
    ):
        node_name = node.__name__
        start = time.perf_counter()
        input_evidence_count = len(state.evidence)
        state = node(state)
        latency_ms = round((time.perf_counter() - start) * 1000, 3)
        trace = NodeTrace(
            request_id=state.request_id,
            node_name=node_name,
            model_used=state.node_models.get(node_name),
            latency_ms=latency_ms,
            input_evidence_count=input_evidence_count,
            output_evidence_count=len(state.evidence),
            fallback_used=state.node_fallbacks.get(node_name, False),
            metadata=state.node_metadata.get(node_name, {}),
        )
        state.trace.append(trace)
        logger.info(
            "request_id=%s node=%s latency_ms=%.3f fallback=%s",
            state.request_id,
            node_name,
            latency_ms,
            trace.fallback_used,
        )
    return state


def run_query(
    repo_id: str,
    question: str,
    task_type: str = "auto",
    context: dict | None = None,
) -> dict:
    state = GraphState(
        repo_id=repo_id,
        question=question,
        task_type=task_type,  # type: ignore[arg-type]
        context=context or {},
    )
    final_state = run_graph(state)
    return {
        "request_id": final_state.request_id,
        "task_type": final_state.task_type,
        "result": final_state.result,
        "trace": [item.model_dump() for item in final_state.trace],
    }
