"""Conservative built-in tools for common EIS development operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from eis.tools.execution import LocalSubprocessBackend, safe_path
from eis.tools.models import (
    ExecutionPolicy,
    ExecutionStatus,
    RiskLevel,
    ToolDefinition,
    ToolRequest,
    ToolResult,
    ToolSchema,
)
from eis.tools.policies import ToolSecurityError


def _schema(properties: dict[str, Any], required: list[str]) -> ToolSchema:
    return ToolSchema({"type": "object", "properties": properties, "required": required})


class FilesystemTool:
    definition = ToolDefinition(
        "filesystem",
        "Read or write files below an explicitly configured root.",
        _schema(
            {
                "operation": {"type": "string"},
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            ["operation", "path"],
        ),
        ToolSchema({"type": "object"}),
        ("filesystem.read",),
        RiskLevel.MEDIUM,
        15.0,
        ExecutionPolicy.SAFE_WRITE,
    )

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    async def execute(self, request: ToolRequest) -> ToolResult:
        operation = request.arguments.get("operation")
        path = safe_path(self.root, str(request.arguments.get("path", "")))
        if operation == "read":
            if "filesystem.read" not in request.granted_permissions:
                raise ToolSecurityError("missing filesystem.read permission")
            return ToolResult(ExecutionStatus.SUCCESS, output=path.read_text())
        if operation == "write":
            if "filesystem.write" not in request.granted_permissions:
                raise ToolSecurityError("missing filesystem.write permission")
            content = request.arguments.get("content")
            if not isinstance(content, str):
                return ToolResult(ExecutionStatus.FAILED, error="content must be a string")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            return ToolResult(ExecutionStatus.SUCCESS, output={"path": str(path)})
        return ToolResult(ExecutionStatus.FAILED, error="unsupported filesystem operation")


class ShellTool:
    """Allowlisted argv execution; shell syntax and arbitrary command strings are rejected."""

    definition = ToolDefinition(
        "shell",
        "Execute explicitly allowlisted commands without shell interpretation.",
        _schema({"argv": {"type": "array", "items": {"type": "string"}}}, ["argv"]),
        ToolSchema({"type": "object"}),
        ("shell.execute",),
        RiskLevel.HIGH,
        30.0,
        ExecutionPolicy.HIGH_RISK,
    )

    def __init__(self, allowed_commands: frozenset[str]) -> None:
        self.allowed_commands = allowed_commands
        self.backend = LocalSubprocessBackend()

    async def execute(self, request: ToolRequest) -> ToolResult:
        if "shell.execute" not in request.granted_permissions:
            raise ToolSecurityError("missing shell.execute permission")
        argv = request.arguments.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
            return ToolResult(ExecutionStatus.FAILED, error="argv must be a non-empty string list")
        if argv[0] not in self.allowed_commands:
            raise ToolSecurityError(f"command is not allowlisted: {argv[0]}")
        if any(token in {";", "&&", "||", "|", ">", ">>"} for token in argv):
            raise ToolSecurityError("shell metacharacters are prohibited")
        return await self.backend.run("shell", {"argv": argv}, self.definition.timeout_seconds)


class GitTool(ShellTool):
    definition = ToolDefinition(
        "git",
        "Inspect a repository using a restricted read-only Git command set.",
        _schema({"argv": {"type": "array", "items": {"type": "string"}}}, ["argv"]),
        ToolSchema({"type": "object"}),
        ("git.read",),
        RiskLevel.LOW,
        30.0,
        ExecutionPolicy.READ_ONLY,
    )

    def __init__(self) -> None:
        super().__init__(frozenset({"git"}))

    async def execute(self, request: ToolRequest) -> ToolResult:
        if "git.read" not in request.granted_permissions:
            raise ToolSecurityError("missing git.read permission")
        argv = request.arguments.get("argv")
        allowed = {"status", "diff", "log", "show", "branch", "rev-parse", "ls-files"}
        if not isinstance(argv, list) or len(argv) < 2 or argv[1] not in allowed:
            raise ToolSecurityError("git operation is not allowlisted")
        return await self.backend.run("git", {"argv": argv}, self.definition.timeout_seconds)


class RepositoryInspectionTool(FilesystemTool):
    definition = ToolDefinition(
        "repository.inspect",
        "Inspect repository files without permitting writes.",
        _schema(
            {"operation": {"type": "string"}, "path": {"type": "string"}},
            ["operation", "path"],
        ),
        ToolSchema({"type": "object"}),
        ("repository.read",),
        RiskLevel.LOW,
        15.0,
        ExecutionPolicy.READ_ONLY,
    )

    async def execute(self, request: ToolRequest) -> ToolResult:
        if "repository.read" not in request.granted_permissions:
            raise ToolSecurityError("missing repository.read permission")
        if request.arguments.get("operation") != "read":
            raise ToolSecurityError("repository inspection is read-only")
        return await super().execute(
            ToolRequest(
                request.tool,
                {"operation": "read", "path": request.arguments.get("path", "")},
                frozenset({"filesystem.read"}),
                request.agent_id,
                request.task_id,
                request.request_id,
            )
        )


class TestExecutionTool(ShellTool):
    definition = ToolDefinition(
        "tests",
        "Run a restricted test command for the current project.",
        _schema({"argv": {"type": "array", "items": {"type": "string"}}}, ["argv"]),
        ToolSchema({"type": "object"}),
        ("tests.execute",),
        RiskLevel.MEDIUM,
        120.0,
        ExecutionPolicy.CONTROLLED_WRITE,
    )

    def __init__(self) -> None:
        super().__init__(frozenset({"pytest"}))

    async def execute(self, request: ToolRequest) -> ToolResult:
        if "tests.execute" not in request.granted_permissions:
            raise ToolSecurityError("missing tests.execute permission")
        argv = request.arguments.get("argv")
        if not isinstance(argv, list) or argv[:1] != ["pytest"]:
            raise ToolSecurityError("only pytest is allowed")
        return await self.backend.run("tests", {"argv": argv}, self.definition.timeout_seconds)


class PythonExecutionTool:
    """Present for capability discovery but prohibited from local unrestricted execution."""

    definition = ToolDefinition(
        "python",
        "Execute Python code in a sandbox-capable backend; local execution is prohibited.",
        _schema({"code": {"type": "string"}}, ["code"]),
        ToolSchema({"type": "object"}),
        ("python.execute",),
        RiskLevel.CRITICAL,
        30.0,
        ExecutionPolicy.PROHIBITED,
    )

    async def execute(self, request: ToolRequest) -> ToolResult:
        del request
        raise ToolSecurityError("local Python execution is prohibited")


class HttpTool:
    definition = ToolDefinition(
        "http",
        "Perform HTTP requests only to explicitly allowlisted hosts.",
        _schema(
            {
                "method": {"type": "string"},
                "url": {"type": "string"},
                "json": {"type": "object"},
            },
            ["method", "url"],
        ),
        ToolSchema({"type": "object"}),
        ("http.request",),
        RiskLevel.MEDIUM,
        30.0,
        ExecutionPolicy.READ_ONLY,
    )

    def __init__(self, allowed_hosts: frozenset[str]) -> None:
        self.allowed_hosts = allowed_hosts

    async def execute(self, request: ToolRequest) -> ToolResult:
        if "http.request" not in request.granted_permissions:
            raise ToolSecurityError("missing http.request permission")
        method = str(request.arguments.get("method", "GET")).upper()
        url = str(request.arguments.get("url", ""))
        parsed = httpx.URL(url)
        if parsed.scheme != "https" or parsed.host not in self.allowed_hosts:
            raise ToolSecurityError("HTTP target is not allowlisted HTTPS")
        if method not in {"GET", "HEAD"}:
            raise ToolSecurityError("only GET and HEAD are permitted by this tool")
        async with httpx.AsyncClient(
            timeout=self.definition.timeout_seconds,
            follow_redirects=False,
        ) as client:
            response = await client.request(method, url)
        return ToolResult(
            ExecutionStatus.SUCCESS if response.is_success else ExecutionStatus.FAILED,
            output={"status_code": response.status_code, "body": response.text},
        )


def default_tools(root: Path, *, http_hosts: frozenset[str] = frozenset()) -> dict[str, Any]:
    """Return safe defaults; shell has no commands until explicitly configured."""
    return {
        "filesystem": FilesystemTool(root),
        "shell": ShellTool(frozenset()),
        "git": GitTool(),
        "repository.inspect": RepositoryInspectionTool(root),
        "tests": TestExecutionTool(),
        "python": PythonExecutionTool(),
        "http": HttpTool(http_hosts),
    }


__all__ = [
    "FilesystemTool",
    "GitTool",
    "HttpTool",
    "PythonExecutionTool",
    "RepositoryInspectionTool",
    "ShellTool",
    "TestExecutionTool",
    "default_tools",
]
