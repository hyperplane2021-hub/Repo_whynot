import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def disable_llm_for_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REPOOPS_ENABLE_LLM_SYNTHESIS", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()

