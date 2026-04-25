from pathlib import Path


class PathValidationError(ValueError):
    pass


def resolve_repo_path(repo_root: Path, user_path: str | Path) -> Path:
    root = repo_root.resolve()
    candidate = (root / user_path).resolve()
    if candidate != root and root not in candidate.parents:
        raise PathValidationError(f"Path escapes repo root: {user_path}")
    return candidate


def clamp_limit(limit: int, minimum: int = 1, maximum: int = 50) -> int:
    return max(minimum, min(maximum, limit))

