import asyncio
from pathlib import Path

from eis.context.models import ContextResult, Query
from eis.engineering import (
    EngineeringAgent,
    EngineeringLimits,
    EngineeringPlan,
    EngineeringTask,
    FileChange,
    RepositorySnapshot,
)
from eis.tools.models import ExecutionStatus, ToolRequest, ToolResult


class FixtureRetriever:
    async def retrieve(self, request):
        return ContextResult(Query(request.query, request.query.lower(), tuple(request.query.split())), ())


class FixtureInspector:
    def __init__(self, root: Path):
        self.root = root

    async def inspect(self, repository):
        files = tuple(str(path.relative_to(self.root)) for path in self.root.rglob("*"))
        return RepositorySnapshot(repository, files=files, architecture=("fixture architecture",))


class FixturePlanner:
    async def plan(self, task, snapshot, context):
        assert snapshot.files
        return EngineeringPlan(
            task.objective,
            "reuse the existing fixture abstraction",
            ("fixture.py",),
            ("fixture.py",),
            ("modify fixture.py",),
            ("targeted tests", "broader tests"),
        )


class FixtureValidator:
    def __init__(self, valid=True):
        self.valid = valid

    async def validate(self, task, snapshot, plan):
        return self.valid, "accepted" if self.valid else "existing abstraction is incompatible"


class FixtureTools:
    def __init__(self, fail_targeted=False):
        self.calls = []
        self.fail_targeted = fail_targeted

    async def execute(self, request: ToolRequest):
        self.calls.append(request.tool)
        if request.tool == "engineering.implement":
            return ToolResult(
                ExecutionStatus.SUCCESS,
                output={
                    "changes": [
                        FileChange("fixture.py", "modify", "updated fixture"),
                        FileChange("test_fixture.py", "modify", "added coverage"),
                    ]
                },
            )
        if request.tool == "engineering.test.targeted" and self.fail_targeted:
            return ToolResult(ExecutionStatus.FAILED, error="targeted test failed")
        if request.tool == "engineering.correct":
            return ToolResult(ExecutionStatus.SUCCESS)
        return ToolResult(ExecutionStatus.SUCCESS)


class FixtureFailureAnalyzer:
    async def analyze(self, result):
        return result.error or "unknown failure"


def make_agent(tmp_path, *, valid=True, fail_targeted=False, limits=None):
    fixture = tmp_path / "fixture.py"
    fixture.write_text("class Existing: pass\n", encoding="utf-8")
    tools = FixtureTools(fail_targeted=fail_targeted)
    agent = EngineeringAgent(
        FixtureRetriever(),
        FixtureInspector(tmp_path),
        FixturePlanner(),
        FixtureValidator(valid),
        tools,
        failure_analyzer=FixtureFailureAnalyzer(),
        limits=limits,
    )
    return agent, tools


def test_engineering_agent_inspects_and_plans_before_implementation(tmp_path):
    agent, tools = make_agent(tmp_path)

    report = asyncio.run(agent.run(EngineeringTask("add feature", str(tmp_path))))

    assert report.status == "completed"
    assert report.plan is not None
    assert tools.calls.index("engineering.implement") > 0
    assert tools.calls[-2:] == ["engineering.test.targeted", "engineering.test.broader"]
    assert report.changes


def test_rejected_plan_never_starts_implementation(tmp_path):
    agent, tools = make_agent(tmp_path, valid=False)

    report = asyncio.run(agent.run(EngineeringTask("unsafe feature", str(tmp_path))))

    assert report.escalated
    assert "engineering.implement" not in tools.calls


def test_file_change_limit_escalates(tmp_path):
    agent, tools = make_agent(tmp_path, limits=EngineeringLimits(max_files_changed=1))

    report = asyncio.run(agent.run(EngineeringTask("feature", str(tmp_path))))

    assert report.escalated
    assert "maximum changed-file limit" in report.escalation_reason
    assert tools.calls == ["engineering.implement"]


def test_failed_targeted_tests_are_analyzed_and_corrected(tmp_path):
    agent, tools = make_agent(tmp_path, fail_targeted=True, limits=EngineeringLimits(max_iterations=1))

    report = asyncio.run(agent.run(EngineeringTask("feature", str(tmp_path))))

    assert report.escalated
    assert "targeted test failed" in report.failures
    assert "engineering.correct" in tools.calls
