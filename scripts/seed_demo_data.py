from pathlib import Path

if __name__ == "__main__":
    sample_repo = Path("data/fixtures/sample_repo")
    print(f"Demo data is already present at {sample_repo.resolve()}")

