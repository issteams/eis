"""Controlled red-team execution and formal assessment."""

from __future__ import annotations

import inspect
from collections.abc import Iterable
from uuid import uuid4

from eis.redteam.models import AttackCase, RedTeamFinding, RedTeamReport
from eis.redteam.protocols import RedTeamTarget


class RedTeamFramework:
    """Attack EIS through an injected target and turn weaknesses into findings."""

    async def run(
        self,
        cases: Iterable[AttackCase],
        target: RedTeamTarget,
    ) -> RedTeamReport:
        """Run all controlled attacks and produce a release assessment."""
        case_list = tuple(cases)
        findings: list[RedTeamFinding] = []
        blocked = 0
        safe = 0

        for case in case_list:
            observation = target(case)
            if inspect.isawaitable(observation):
                observation = await observation
            if observation.case_id != case.id:
                raise ValueError(f"target returned case {observation.case_id!r} for {case.id!r}")
            if observation.blocked:
                blocked += 1
            if observation.safe:
                safe += 1
            if not observation.safe:
                findings.append(RedTeamFinding(case, observation))

        return RedTeamReport(
            run_id=str(uuid4()),
            total_cases=len(case_list),
            blocked=blocked,
            safe=safe,
            findings=tuple(findings),
        )


__all__ = ["RedTeamFramework"]
