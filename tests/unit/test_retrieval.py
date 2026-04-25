from pathlib import Path

from app.rag.indexer import build_index
from app.rag.retrievers import retrieve_code, retrieve_docs, retrieve_history


def test_keyword_retrieval_three_lanes() -> None:
    build_index(Path("data/fixtures/sample_repo"), "sample/repo")
    assert retrieve_docs("sample/repo", "token lifecycle")
    assert retrieve_code("sample/repo", "TokenRefreshError")
    assert retrieve_history("sample/repo", "Login fails token")

