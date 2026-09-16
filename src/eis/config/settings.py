"""Typed, environment-driven EIS configuration."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EIS_", env_file=".env", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"
    model_provider: str = "none"
    embedding_provider: str = "none"
    repository_provider: str = "none"
    knowledge_backend: str = "none"
    max_tool_calls: int = Field(default=20, ge=0, le=1000)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
