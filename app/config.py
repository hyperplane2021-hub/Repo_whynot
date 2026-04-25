from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    env: str = "local"
    model_provider: str = "none"
    model_name: str = "gpt-5.4-mini"
    openai_api_key: str | None = None
    github_token: str | None = None
    enable_llm_synthesis: bool = False
    index_root: Path = Path("data/indexes")
    max_tool_rounds: int = 2
    max_tool_calls_per_round: int = 3
    max_evidence_items: int = 8
    max_investigation_rounds: int = 2
    max_investigation_queries_per_round: int = 3
    github_search_cache: bool = True

    model_config = SettingsConfigDict(env_prefix="REPOOPS_", env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]
