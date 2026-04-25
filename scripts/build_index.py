from pathlib import Path

from app.rag.indexer import build_index

if __name__ == "__main__":
    stats = build_index(Path("data/fixtures/sample_repo"), "sample/repo")
    print(stats.model_dump_json(indent=2))

