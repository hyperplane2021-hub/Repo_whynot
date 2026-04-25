import math
import re
from collections import Counter

from app.rag.indexer import load_index
from app.rag.types import IndexDocument, RetrievalResult

TOKEN_RE = re.compile(r"[A-Za-z0-9_\u4e00-\u9fff]+")


class KeywordRetriever:
    def __init__(self, documents: list[IndexDocument]) -> None:
        self.documents = documents
        self.doc_tokens = [
            Counter(tokenize(doc.text + " " + _metadata_text(doc))) for doc in documents
        ]
        self.document_frequency = Counter()
        for tokens in self.doc_tokens:
            self.document_frequency.update(tokens.keys())

    def search(
        self,
        query: str,
        k: int = 5,
        source_type: str | None = None,
    ) -> list[RetrievalResult]:
        query_tokens = Counter(tokenize(query))
        if not query_tokens:
            return []
        results: list[RetrievalResult] = []
        total_docs = max(1, len(self.documents))
        for doc, tokens in zip(self.documents, self.doc_tokens, strict=True):
            if source_type and doc.source_type != source_type:
                continue
            score = 0.0
            for token, query_count in query_tokens.items():
                tf = tokens.get(token, 0)
                if not tf:
                    continue
                idf = math.log((1 + total_docs) / (1 + self.document_frequency[token])) + 1
                score += min(tf, 3) * query_count * idf
            if score > 0:
                results.append(RetrievalResult(document=doc, score=round(score, 4)))
        return sorted(results, key=lambda item: item.score, reverse=True)[:k]


class VectorRetriever:
    def add_documents(self, docs: list[IndexDocument]) -> None:
        self.documents = docs

    def search(self, query: str, k: int) -> list[RetrievalResult]:
        return []


def retrieve_docs(repo_id: str, query: str, k: int = 5) -> list[RetrievalResult]:
    return KeywordRetriever(load_index(repo_id)).search(query, k=k, source_type="doc")


def retrieve_code(repo_id: str, query: str, k: int = 5) -> list[RetrievalResult]:
    return KeywordRetriever(load_index(repo_id)).search(query, k=k, source_type="code")


def retrieve_history(repo_id: str, query: str, k: int = 5) -> list[RetrievalResult]:
    docs = load_index(repo_id)
    results: list[RetrievalResult] = []
    retriever = KeywordRetriever(docs)
    for source_type in ("issue", "pr", "commit"):
        results.extend(retriever.search(query, k=k, source_type=source_type))
    return sorted(results, key=lambda item: item.score, reverse=True)[:k]


def retrieve_all(repo_id: str, query: str, k_per_source: int = 5) -> list[RetrievalResult]:
    return (
        retrieve_docs(repo_id, query, k_per_source)
        + retrieve_code(repo_id, query, k_per_source)
        + retrieve_history(repo_id, query, k_per_source)
    )


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def _metadata_text(doc: IndexDocument) -> str:
    values = [str(value) for value in doc.metadata.values() if isinstance(value, str | int)]
    list_values = [" ".join(value) for value in doc.metadata.values() if isinstance(value, list)]
    return " ".join(values + list_values)
