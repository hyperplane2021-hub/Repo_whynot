from pathlib import Path

import pytest

from app.tools.read_only import grep_repo, read_file, search_issues
from app.tools.validation import PathValidationError, resolve_repo_path

REPO = Path("data/fixtures/sample_repo")


def test_path_validation_blocks_escape() -> None:
    with pytest.raises(PathValidationError):
        resolve_repo_path(REPO, "../README.md")


def test_read_file() -> None:
    result = read_file(REPO, "README.md")
    assert result["path"] == "README.md"
    assert "Authentication" in result["content"]


def test_grep_repo() -> None:
    results = grep_repo(REPO, "TokenRefreshError")
    assert any(result["path"] == "src/auth/session.py" for result in results)


def test_search_issues() -> None:
    results = search_issues(REPO, "Login token")
    assert results[0]["number"] == 12

