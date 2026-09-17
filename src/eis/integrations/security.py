"""Security boundary used by all external integration adapters."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Awaitable, Callable, TypeVar

from eis.security.models import ActionRequest, Approval, Principal, RiskLevel
from eis.security.runtime import SecurityGateway

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class IntegrationSecurity:
    """Require EIS authorization before an adapter touches an external system."""

    gateway: SecurityGateway
    principal: Principal

    async def read(
        self,
        resource: str,
        *,
        operation: str,
        action: Callable[[], T | Awaitable[T]],
    ) -> T:
        request = ActionRequest(self.principal, "read", resource, target=operation)
        self.gateway.prepare(request)
        try:
            result = action()
            if inspect.isawaitable(result):
                result = await result
        except Exception as exc:
            self.gateway.complete(request, result="failed", failure=str(exc))
            raise
        self.gateway.complete(request)
        return result

    async def write(
        self,
        resource: str,
        *,
        operation: str,
        action: Callable[[], T | Awaitable[T]],
        approval: Approval | None = None,
    ) -> T:
        request = ActionRequest(
            self.principal,
            "write",
            resource,
            risk_level=RiskLevel.HIGH,
            target=operation,
        )
        self.gateway.prepare(request, approval=approval)
        try:
            result = action()
            if inspect.isawaitable(result):
                result = await result
        except Exception as exc:
            self.gateway.complete(request, result="failed", failure=str(exc))
            raise
        self.gateway.complete(request)
        return result


__all__ = ["IntegrationSecurity"]
