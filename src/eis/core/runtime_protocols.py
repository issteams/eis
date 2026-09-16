"""Stable runtime lifecycle and event contracts."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from eis.core.context import EISContext
from eis.core.events import EISEvent
from eis.core.hierarchy import OrganizationHierarchy
from eis.core.identity import RequestIdentity, SessionIdentity

EventHandler = Callable[[EISEvent], None]


class Runtime(Protocol):
    """Contract implemented by the EIS application runtime."""

    def start(self) -> None: ...
    def stop(self) -> None: ...
    def subscribe(self, handler: EventHandler) -> None: ...
    def emit(self, event: EISEvent) -> None: ...

    def create_context(
        self,
        hierarchy: OrganizationHierarchy,
        *,
        session: SessionIdentity | None = None,
        request: RequestIdentity | None = None,
    ) -> EISContext: ...
