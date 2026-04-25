from app.graph.state import GraphState
from app.services.approvals import approval_gate


def action_gate(state: GraphState) -> GraphState:
    state.action_status = approval_gate(state.result or {})
    return state

