"""Result and lifecycle status abstractions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeVar

T = TypeVar("T")


class Status(StrEnum):
    """Stable status values shared by runtime operations."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class Result(Generic[T]):
    """Explicit success/failure result without provider-specific behavior."""

    status: Status
    value: T | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status is Status.SUCCEEDED and self.error is None

    @classmethod
    def success(cls, value: T) -> "Result[T]":
        return cls(status=Status.SUCCEEDED, value=value)

    @classmethod
    def failure(cls, error: str, *, status: Status = Status.FAILED) -> "Result[T]":
        if not error.strip():
            raise ValueError("error must not be empty")
        return cls(status=status, error=error)
