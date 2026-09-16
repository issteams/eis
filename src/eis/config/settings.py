"""Typed, environment-driven EIS configuration."""

from enum import StrEnum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Supported EIS runtime environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Validated runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_prefix="EIS_", env_file=".env", extra="ignore")

    environment: Environment = Environment.DEVELOPMENT
    runtime_name: str = Field(default="eis", min_length=1)
    log_level: str = "INFO"
    model_provider: str = "none"
    model_name: str = ""
    model_base_url: str = ""
    model_api_key: str = ""
    model_timeout: float = Field(default=60.0, gt=0)
    model_max_attempts: int = Field(default=3, ge=1, le=10)
    embedding_provider: str = "none"
    repository_provider: str = "none"
    knowledge_backend: str = "none"
    max_tool_calls: int = Field(default=20, ge=0, le=1000)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide validated settings instance."""
    return Settings()
