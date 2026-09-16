"""Structured provider-independent model errors."""

from __future__ import annotations


class ModelError(Exception):
    """Base error for model operations."""

    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable


class ModelConfigurationError(ModelError):
    """Provider/model configuration is invalid or incomplete."""


class ModelValidationError(ModelError):
    """The provider rejected an otherwise well-formed model operation."""


class ModelTimeoutError(ModelError):
    """A model operation exceeded its timeout."""


class ModelRateLimitError(ModelError):
    """The provider rate-limited a request."""

    def __init__(
        self,
        message: str,
        *,
        retry_after: float | None = None,
        provider: str | None = None,
    ) -> None:
        super().__init__(message, provider=provider, retryable=True)
        self.retry_after = retry_after


class ModelUnavailableError(ModelError):
    """The provider is unavailable or failed transiently."""

    def __init__(self, message: str, *, provider: str | None = None) -> None:
        super().__init__(message, provider=provider, retryable=True)
