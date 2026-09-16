# EIS Autonomous Software Engineering Agent

Phase 9 adds a bounded, repository-aware engineering workflow to EIS.

## Safety boundary

The agent cannot implement a task immediately. It must first retrieve project knowledge, inspect the repository, build an engineering plan, and pass plan validation. Only then may it invoke the implementation tool.

Implementation remains behind the Phase 8 secure tool execution layer. The engineering agent does not receive unrestricted shell or filesystem access.

## Workflow

1. Understand requirement.
2. Retrieve relevant project knowledge.
3. Inspect repository.
4. Understand architecture.
5. Identify affected components.
6. Identify existing functionality.
7. Detect duplication.
8. Produce structured implementation plan.
9. Validate the plan.
10. Implement changes.
11. Run targeted tests.
12. Run broader tests.
13. Analyze failures.
14. Correct implementation when bounded retries remain.
15. Re-run tests.
16. Produce implementation report.

Repository inspection produces a `RepositorySnapshot` containing files, architecture notes, existing functionality, relevant sources, and duplication candidates. The planner receives this snapshot and retrieved context so reuse can be preferred over new abstractions.

## Autonomous limits

`EngineeringLimits` controls:

- `max_iterations`
- `max_files_changed`
- `max_execution_seconds`
- `max_tool_calls`

When a limit is reached, or a plan is rejected, the agent stops and returns an escalated `EngineeringReport` instead of continuing autonomously.

## Change tracking

Every reported file modification is converted into a `FileChange` and recorded by a `ChangeTracker`. The final report contains phase-level `ChangeRecord` entries, test stages, failures, iteration count, tool-call count, and a change summary.

## Replaceable boundaries

Repository inspection, knowledge retrieval, planning, plan validation, failure analysis, change tracking, and tool execution are protocols. This keeps the engineering workflow independent of a particular model, repository provider, or execution environment and allows future sandbox/container implementations without changing the engineering-agent API.

## Testing

`tests/test_engineering_agent.py` uses a controlled temporary fixture repository and verifies:

- repository inspection precedes implementation;
- rejected plans never invoke implementation;
- changed-file limits trigger escalation;
- failed targeted tests are analyzed and routed to bounded correction.
