"""Protocols for controlled EIS red-team execution."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import Protocol

from eis.redteam.models import (
    AttackCase,
    AttackObservation,
)


RedTeamTarget = Callable[[AttackCase], AttackObservation | Awaitable[AttackObservation]]


class RedTeamRunner(Protocol):
    """Execute one adversarial case against an EIS target."""

    def run(self, case: AttackCase) -> AttackObservation | Awaitable[AttackObservation]: ...


class RedTeamSuite(Protocol):
    """Provide cases belonging to a red-team suite."""

    def cases(self) -> Sequence[AttackCase]: ...


__all__ = ["RedTeamRunner", "RedTeamSuite", "RedTeamTarget"]
