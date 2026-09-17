"""Liveness/readiness probes with dependency checks."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    ok: bool
    detail: str = ""


class HealthRegistry:
    """Registry for cheap liveness and dependency readiness checks."""

    def __init__(self) -> None:
        self._checks: dict[str, Callable[[], bool | CheckResult]] = {}
        self._ready = True

    def register(self, name: str, check: Callable[[], bool | CheckResult]) -> None:
        self._checks[name] = check

    def set_not_ready(self) -> None:
        self._ready = False

    def set_ready(self) -> None:
        self._ready = True

    def liveness(self) -> dict[str, Any]:
        return {"status": "ok"}

    def readiness(self) -> dict[str, Any]:
        if not self._ready:
            return {"status": "not_ready", "checks": []}
        results: list[CheckResult] = []
        for name, check in self._checks.items():
            try:
                value = check()
                result = value if isinstance(value, CheckResult) else CheckResult(name, value)
            except Exception as exc:
                result = CheckResult(name, False, str(exc))
            results.append(result)
        ok = all(result.ok for result in results)
        return {
            "status": "ready" if ok else "not_ready",
            "checks": [
                {"name": result.name, "ok": result.ok, "detail": result.detail}
                for result in results
            ],
        }

    def health(self) -> dict[str, Any]:
        readiness = self.readiness()
        return {"status": "ok" if readiness["status"] == "ready" else "degraded", **readiness}


__all__ = ["CheckResult", "HealthRegistry"]
