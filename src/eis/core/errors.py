"""Domain-neutral EIS exception hierarchy."""


class EISError(Exception):
    """Base exception for expected EIS failures."""


class ConfigurationError(EISError):
    """Configuration is missing or invalid."""


class IntegrityError(EISError):
    """A trust or evidence invariant was violated."""


class ExecutionError(EISError):
    """A requested operation could not be executed."""


class ProviderError(EISError):
    """An external provider failed or returned unusable data."""


class SecurityError(EISError):
    """A security policy prevented an operation."""


class LifecycleError(EISError):
    """A runtime lifecycle transition is invalid."""


class ContextError(EISError):
    """A runtime context is invalid or incomplete."""


class ResultError(EISError):
    """A result violates a result invariant."""
