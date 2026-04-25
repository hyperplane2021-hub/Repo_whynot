from app.config import get_settings
from app.graph.state import GraphState
from app.rag.types import IndexDocument, RetrievalResult
from app.schemas.common import EvidenceItem


def evidence_merge(state: GraphState) -> GraphState:
    seen: set[str] = set()
    evidence: list[EvidenceItem] = []
    for result in sorted(state.retrieval_results, key=lambda item: item.score, reverse=True):
        doc = result.document
        key = _evidence_key(doc)
        if key in seen:
            continue
        seen.add(key)
        evidence.append(_to_evidence(result, len(evidence) + 1))
        if len(evidence) >= get_settings().max_evidence_items:
            break
    state.evidence = evidence
    state.candidate_evidence = evidence
    state.node_metadata["evidence_merge"] = {"candidate_evidence": len(evidence)}
    return state


def _to_evidence(result: RetrievalResult, index: int) -> EvidenceItem:
    doc = result.document
    metadata = doc.metadata
    return EvidenceItem(
        evidence_id=f"E{index}",
        source_type=doc.source_type,  # type: ignore[arg-type]
        title=metadata.get("title") or metadata.get("message") or metadata.get("section_title"),
        path=metadata.get("path"),
        number=metadata.get("number"),
        start_line=metadata.get("start_line"),
        end_line=metadata.get("end_line"),
        snippet=_snippet(doc.text),
        score=result.score,
    )


def _snippet(text: str, limit: int = 360) -> str:
    compact = " ".join(text.split())
    return compact[:limit]


def _evidence_key(doc: IndexDocument) -> str:
    metadata = doc.metadata
    return ":".join(
        [
            str(doc.source_type),
            str(metadata.get("path") or metadata.get("number") or metadata.get("sha") or doc.id),
            str(metadata.get("start_line", "")),
        ]
    )
