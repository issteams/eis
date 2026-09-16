from __future__ import annotations
from typing import Protocol


class Authorizer(Protocol):
    def allowed(self, principal: str, action: str, resource: str) -> bool: ...


__all__ = ["Authorizer"]
