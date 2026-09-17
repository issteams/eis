"""EIS red-team and failure-engineering public surface."""

from eis.redteam.cases import CASES, builtin_cases
from eis.redteam.models import (
    AttackCase,
    AttackCategory,
    AttackObservation,
    AttackSeverity,
    RedTeamFinding,
    RedTeamReport,
)
from eis.redteam.runtime import RedTeamFramework

__all__ = [
    "CASES",
    "AttackCase",
    "AttackCategory",
    "AttackObservation",
    "AttackSeverity",
    "RedTeamFinding",
    "RedTeamFramework",
    "RedTeamReport",
    "builtin_cases",
]
