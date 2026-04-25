def approval_gate(result: dict) -> str:
    if result.get("draft_actions"):
        return "pending_approval"
    return "read_only"

