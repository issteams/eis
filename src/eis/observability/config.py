"""Environment-driven production configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class ProductionSettings(BaseSettings):
    """Deployment settings; secrets must be supplied by the environment or secret manager."""

    service_name: str = "eis"
    environment: str = "development"
    log_json: bool = True
    log_level: str = "INFO"
    request_timeout_seconds: float = 30.0
    model_timeout_seconds: float = 120.0
    tool_timeout_seconds: float = 120.0
    max_retries: int = 2
    retry_backoff_seconds: float = 0.5
    worker_concurrency: int = 4
    queue_name: str = "eis"
    max_concurrent_tasks: int = 4
    task_lease_seconds: int = 300
    task_recovery_interval_seconds: int = 30
    max_task_attempts: int = 3
    health_timeout_seconds: float = 2.0
    persistence_path: str = "eis-jobs.sqlite3"
    metrics_enabled: bool = True

    model_config = SettingsConfigDict(env_prefix="EIS_", env_file=".env", extra="ignore")

    def validate(self) -> None:
        if self.request_timeout_seconds <= 0 or self.model_timeout_seconds <= 0:
            raise ValueError("timeouts must be positive")
        if self.max_retries < 0 or self.max_task_attempts < 1:
            raise ValueError("retry and attempt limits are invalid")
        if self.worker_concurrency < 1 or self.max_concurrent_tasks < 1:
            raise ValueError("worker concurrency must be positive")


__all__ = ["ProductionSettings"]
