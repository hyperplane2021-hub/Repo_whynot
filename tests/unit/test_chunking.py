from pathlib import Path

from app.rag.chunkers import chunk_code, chunk_markdown


def test_markdown_chunk_metadata() -> None:
    docs = chunk_markdown(
        Path("data/fixtures/sample_repo/README.md"),
        Path("data/fixtures/sample_repo"),
    )
    assert docs
    assert docs[0].metadata["source_type"] == "doc"
    assert docs[0].metadata["path"] == "README.md"


def test_code_chunk_metadata() -> None:
    docs = chunk_code(
        Path("data/fixtures/sample_repo/src/auth/session.py"),
        Path("data/fixtures/sample_repo"),
    )
    assert docs
    assert docs[0].metadata["language"] == "python"
    assert docs[0].metadata["start_line"] == 1
