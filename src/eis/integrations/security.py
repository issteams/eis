"""Security boundary used by all external integration adapters."""

from __future__ import annotations

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

    def check_read(self, resource: str, *, operation: str) -> None:
        self.gateway.execute_approved(
            ActionRequest(
                self.principal,
                "read",
                resource,
                target=operation,
            )
        )

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
        self.gateway.execute_approved(request, approval=approval)
        result = action()
        if hasattr(result, "__await__"):
            return await result  # type: ignore[misc]
        return result


__all__ = ["IntegrationSecurity"]
