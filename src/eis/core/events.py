"""Structured runtime events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from eis.core.identity import CorrelationId


@dataclass(frozen=True, slots=True)
class EISEvent:
    """Provider-neutral event emitted by the runtime lifecycle."""

    event_type: str
    correlation_id: CorrelationId
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: UUID = field(default_factory=uuid4)
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_type.strip():
            raise ValueError("event_type must not be empty")
        if self.timestamp.tzinfo is None:
            raise ValueError("event timestamp must be timezone-aware")
