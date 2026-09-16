import asyncio
from pathlib import Path

import pytest

from eis.tools import (
    ExecutionLimits,
    ExecutionPolicy,
    ExecutionStatus,
    FilesystemTool,
    InMemoryAuditSink,
    PythonExecutionTool,
    SecureExecutor,
    ShellTool,
    ToolRequest,
    ToolSecurityError,
)
from eis.tools.models import RiskLevel, ToolDefinition, ToolResult, ToolSchema


def run(coro):
    return asyncio.run(coro)


def test_filesystem_is_rooted_and_reads_with_permission(tmp_path: Path):
    (tmp_path / "safe.txt").write_text("hello")
    tool = FilesystemTool(tmp_path)
    result = run(
        tool.execute(
            ToolRequest(
                "filesystem",
                {"operation": "read", "path": "safe.txt"},
                frozenset({"filesystem.read"}),
            )
        )
    )
    assert result.status is ExecutionStatus.SUCCESS
    assert result.output == "hello"


def test_path_traversal_is_rejected(tmp_path: Path):
    tool = FilesystemTool(tmp_path)
    with pytest.raises(ToolSecurityError, match="path escapes"):
        run(
            tool.execute(
                ToolRequest(
                    "filesystem",
                    {"operation": "read", "path": "../outside.txt"},
                    frozenset({"filesystem.read"}),
                )
            )
        )


def test_secure_executor_denies_missing_permission(tmp_path: Path):
    audit = InMemoryAuditSink()
    executor = SecureExecutor({"filesystem": FilesystemTool(tmp_path)}, audit=audit)
    result = run(
        executor.execute(
            ToolRequest("filesystem", {"operation": "read", "path": "x"})
        )
    )
    assert result.status is ExecutionStatus.DENIED
    assert len(audit.events) == 1
    assert audit.events[0].status is ExecutionStatus.DENIED


def test_prohibited_python_never_executes():
    audit = InMemoryAuditSink()
    executor = SecureExecutor({"python": PythonExecutionTool()}, audit=audit)
    result = run(
        executor.execute(
            ToolRequest(
                "python",
                {"code": "raise SystemExit"},
                frozenset({"python.execute"}),
            )
        )
    )
    assert result.status is ExecutionStatus.DENIED
    assert audit.events[0].policy is ExecutionPolicy.PROHIBITED


def test_shell_rejects_arbitrary_commands():
    tool = ShellTool(frozenset({"echo"}))
    with pytest.raises(ToolSecurityError, match="not allowlisted"):
        run(
            tool.execute(
                ToolRequest(
                    "shell",
                    {"argv": ["rm", "-rf", "/"]},
                    frozenset({"shell.execute"}),
                )
            )
        )


def test_shell_rejects_shell_metacharacters():
    tool = ShellTool(frozenset({"echo"}))
    with pytest.raises(ToolSecurityError, match="metacharacters"):
        run(
            tool.execute(
                ToolRequest(
                    "shell",
                    {"argv": ["echo", "ok", ";", "id"]},
                    frozenset({"shell.execute"}),
                )
            )
        )


def test_secure_executor_applies_timeout_and_audits():
    class SlowTool:
        definition = ToolDefinition(
            "slow",
            "test",
            ToolSchema(),
            ToolSchema(),
            ("slow.run",),
            RiskLevel.LOW,
            0.01,
            ExecutionPolicy.READ_ONLY,
        )

        async def execute(self, request):
            await asyncio.sleep(1)
            return ToolResult(ExecutionStatus.SUCCESS, request_id=request.request_id)

    audit = InMemoryAuditSink()
    executor = SecureExecutor({"slow": SlowTool()}, audit=audit)
    result = run(executor.execute(ToolRequest("slow", {}, frozenset({"slow.run"}))))
    assert result.status is ExecutionStatus.TIMEOUT
    assert audit.events[0].status is ExecutionStatus.TIMEOUT


def test_output_is_capped():
    class OutputTool:
        definition = ToolDefinition(
            "output",
            "test",
            ToolSchema(),
            ToolSchema(),
            ("output.read",),
        )

        async def execute(self, request):
            return ToolResult(
                ExecutionStatus.SUCCESS,
                stdout="x" * 100,
                request_id=request.request_id,
            )

    executor = SecureExecutor(
        {"output": OutputTool()},
        audit=InMemoryAuditSink(),
        limits=ExecutionLimits(max_output_bytes=10),
    )
    result = run(executor.execute(ToolRequest("output", {}, frozenset({"output.read"}))))
    assert len(result.stdout) == 10


def test_write_requires_write_permission(tmp_path: Path):
    tool = FilesystemTool(tmp_path)
    with pytest.raises(ToolSecurityError, match=r"filesystem\.write"):
        run(
            tool.execute(
                ToolRequest(
                    "filesystem",
                    {"operation": "write", "path": "x.txt", "content": "blocked"},
                    frozenset({"filesystem.read"}),
                )
            )
        )
    assert not (tmp_path / "x.txt").exists()


def test_execution_limits_reject_excess_arguments(tmp_path: Path):
    executor = SecureExecutor(
        {"filesystem": FilesystemTool(tmp_path)},
        audit=InMemoryAuditSink(),
        limits=ExecutionLimits(max_arguments=1),
    )
    result = run(
        executor.execute(
            ToolRequest(
                "filesystem",
                {"operation": "read", "path": "x"},
                frozenset({"filesystem.read", "filesystem.write"}),
            )
        )
    )
    assert result.status is ExecutionStatus.DENIED
