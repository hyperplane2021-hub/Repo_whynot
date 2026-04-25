from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.rag.indexer import build_index


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_query_api() -> None:
    build_index(Path("data/fixtures/sample_repo"), "sample/repo")
    client = TestClient(app)
    response = client.post(
        "/query",
        json={
            "repo_id": "sample/repo",
            "task_type": "repo_qa",
            "question": "Where is refresh token logic?",
        },
    )
    assert response.status_code == 200
    assert response.json()["result"]["evidence"]
    assert response.json()["trace"]
