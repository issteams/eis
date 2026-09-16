"""Provider-neutral retry and timeout policy."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    initial_delay: float = 0.25
    max_delay: float = 5.0
    multiplier: float = 2.0
    jitter: float = 0.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.initial_delay < 0 or self.max_delay < 0:
            raise ValueError("retry delays cannot be negative")
        if self.max_delay < self.initial_delay:
            raise ValueError("max_delay must be >= initial_delay")
        if self.multiplier < 1:
            raise ValueError("multiplier must be >= 1")
        if self.jitter < 0:
            raise ValueError("jitter cannot be negative")

    def delay(self, attempt: int) -> float:
        """Return the deterministic exponential backoff for an attempt number."""
        if attempt < 1:
            raise ValueError("attempt must be >= 1")
        return min(self.max_delay, self.initial_delay * self.multiplier ** (attempt - 1))
