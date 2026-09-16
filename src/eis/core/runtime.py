"""Core EIS application runtime and lifecycle management."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Callable

from eis.config import Settings
from eis.core.context import EISContext
from eis.core.errors import LifecycleError
from eis.core.events import EISEvent
from eis.core.hierarchy import OrganizationHierarchy
from eis.core.identity import CorrelationId, EISIdentity, RequestIdentity, SessionIdentity


class RuntimeState(StrEnum):
    """Lifecycle state of an EIS runtime instance."""

    CREATED = "created"
    STARTED = "started"
    STOPPED = "stopped"


EventHandler = Callable[[EISEvent], None]


@dataclass(slots=True)
class EISRuntime:
    """Application runtime shared by all future EIS components."""

    settings: Settings
    identity: EISIdentity = field(default_factory=lambda: EISIdentity.create("eis"))
    state: RuntimeState = RuntimeState.CREATED
    _handlers: list[EventHandler] = field(default_factory=list, repr=False)

    @classmethod
    def from_environment(cls) -> "EISRuntime":
        """Construct a runtime using the process environment configuration."""
        return cls(settings=Settings())

    def start(self) -> None:
        """Start the runtime."""
        if self.state is RuntimeState.STOPPED:
            raise LifecycleError("stopped EIS runtime cannot be restarted")
        self.state = RuntimeState.STARTED

    def stop(self) -> None:
        """Stop the runtime."""
        if self.state is RuntimeState.STARTED:
            self.state = RuntimeState.STOPPED

    def subscribe(self, handler: EventHandler) -> None:
        """Register a local event handler."""
        self._handlers.append(handler)

    def emit(self, event: EISEvent) -> None:
        """Publish an event to registered handlers."""
        for handler in tuple(self._handlers):
            handler(event)

    def create_context(
        self,
        hierarchy: OrganizationHierarchy,
        *,
        session: SessionIdentity | None = None,
        request: RequestIdentity | None = None,
    ) -> EISContext:
        """Create a request context with a fresh correlation identifier."""
        return EISContext(
            hierarchy=hierarchy,
            session=session or SessionIdentity.create("session"),
            request=request or RequestIdentity.create(),
            correlation_id=CorrelationId.create(),
        )
