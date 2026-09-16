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
