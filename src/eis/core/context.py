"""Explicit execution context shared by EIS components."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from eis.core.hierarchy import OrganizationHierarchy
from eis.core.identity import CorrelationId, RequestIdentity, SessionIdentity


@dataclass(frozen=True, slots=True)
class EISContext:
    """Immutable context carried through a request/task execution."""

    hierarchy: OrganizationHierarchy
    session: SessionIdentity
    request: RequestIdentity
    correlation_id: CorrelationId
    metadata: dict[str, Any] = field(default_factory=dict)

    def child(self, *, metadata: dict[str, Any] | None = None) -> "EISContext":
        """Create a context preserving correlation while extending metadata."""
        merged = dict(self.metadata)
        if metadata:
            merged.update(metadata)
        return EISContext(
            hierarchy=self.hierarchy,
            session=self.session,
            request=self.request,
            correlation_id=self.correlation_id,
            metadata=merged,
        )
