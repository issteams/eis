"""Secure execution orchestration and local backend primitives."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from eis.tools.models import (
    AuditEvent,
    ExecutionPolicy,
    ExecutionStatus,
    RiskLevel,
    ToolDefinition,
    ToolRequest,
    ToolResult,
    ToolSchema,
)
from eis.tools.policies import ExecutionLimits, SecurityPolicy, ToolSecurityError
from eis.tools.protocols import AuditSink, PolicyAuthorizer


class ToolExecutionError(RuntimeError):
    """Raised for malformed or failed tool execution."""


@dataclass(slots=True)
class InMemoryAuditSink:
    events: list[AuditEvent] = field(default_factory=list)

    def record(self, event: AuditEvent) -> None:
        self.events.append(event)


class SecureExecutor:
    """Execute registered tools only after permission, policy, and limit checks."""

    def __init__(
        self,
        tools: dict[str, Any],
        *,
        audit: AuditSink,
        policy: PolicyAuthorizer | None = None,
        limits: ExecutionLimits | None = None,
    ) -> None:
        self._tools = tools
        self._audit = audit
        self._policy = policy or SecurityPolicy()
        self._limits = limits or ExecutionLimits()

    async def execute(self, request: ToolRequest) -> ToolResult:
        started = time.monotonic()
        definition: ToolDefinition | None = None
        status = ExecutionStatus.FAILED
        error: str | None = None
        result = ToolResult(ExecutionStatus.FAILED, request_id=request.request_id)
        try:
            definition = self._definition(request.tool)
            self._limits.validate(definition, request)
            missing = set(definition.permissions) - set(request.granted_permissions)
            if missing:
                raise ToolSecurityError(f"missing permissions: {', '.join(sorted(missing))}")
            self._policy.authorize(request, definition)
            result = await asyncio.wait_for(
                self._tools[request.tool].execute(request),
                timeout=definition.timeout_seconds,
            )
            result = self._cap_output(result)
            status = result.status
            return result
        except TimeoutError:
            status = ExecutionStatus.TIMEOUT
            error = (
                f"tool timed out after {definition.timeout_seconds:.3f}s"
                if definition is not None
                else "tool timed out"
            )
            return ToolResult(status, error=error, request_id=request.request_id)
        except (ToolSecurityError, PermissionError) as exc:
            status = ExecutionStatus.DENIED
            error = str(exc)
            return ToolResult(status, error=error, request_id=request.request_id)
        except Exception as exc:
            status = ExecutionStatus.FAILED
            error = str(exc)
            return ToolResult(status, error=error, request_id=request.request_id)
        finally:
            if definition is None:
                definition = ToolDefinition(
                    request.tool,
                    "unregistered tool",
                    ToolSchema(),
                    ToolSchema(),
                    risk_level=RiskLevel.CRITICAL,
                    execution_policy=ExecutionPolicy.PROHIBITED,
                )
            self._audit.record(
                AuditEvent(
                    request_id=request.request_id,
                    tool=request.tool,
                    status=status,
                    policy=definition.execution_policy,
                    risk_level=definition.risk_level,
                    agent_id=request.agent_id,
                    task_id=request.task_id,
                    arguments=dict(request.arguments),
                    error=error if error is not None else result.error,
                    duration_seconds=time.monotonic() - started,
                )
            )

    def _definition(self, name: str) -> ToolDefinition:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolExecutionError(f"tool is not registered: {name}")
        return tool.definition

    def _cap_output(self, result: ToolResult) -> ToolResult:
        limit = self._limits.max_output_bytes
        stdout = result.stdout.encode()[:limit].decode(errors="replace")
        stderr = result.stderr.encode()[:limit].decode(errors="replace")
        return ToolResult(
            result.status,
            output=result.output,
            error=result.error,
            exit_code=result.exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=result.duration_seconds,
            request_id=result.request_id,
        )


class AgentToolAdapter:
    """Bridge Phase 7's ``invoke(step)`` API without bypassing agent grants."""

    def __init__(
        self,
        tool_name: str,
        executor: SecureExecutor,
        granted_permissions: frozenset[str],
    ) -> None:
        self.name = tool_name
        self._executor = executor
        self._granted_permissions = granted_permissions
        self.definition = executor._definition(tool_name)

    async def invoke(self, step: Any) -> ToolResult:
        from eis.agents.models import AgentStep

        if not isinstance(step, AgentStep):
            raise TypeError("agent tool adapter requires AgentStep")
        return await self._executor.execute(
            ToolRequest(
                self.name,
                {"step": step.input, "resource": step.resource},
                self._granted_permissions,
            )
        )


@dataclass(frozen=True, slots=True)
class LocalSubprocessBackend:
    """Subprocess backend; only receives validated argv and never invokes a shell."""

    async def run(
        self,
        operation: str,
        arguments: dict[str, Any],
        timeout_seconds: float,
    ) -> ToolResult:
        del operation
        argv = arguments.get("argv")
        if not isinstance(argv, Sequence) or isinstance(argv, (str, bytes)):
            return ToolResult(ExecutionStatus.FAILED, error="argv must be a sequence")
        if not all(isinstance(part, str) and part for part in argv):
            return ToolResult(ExecutionStatus.FAILED, error="argv contains invalid values")
        started = time.monotonic()
        process = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
            return ToolResult(
                ExecutionStatus.SUCCESS if process.returncode == 0 else ExecutionStatus.FAILED,
                stdout=stdout.decode(errors="replace"),
                stderr=stderr.decode(errors="replace"),
                exit_code=process.returncode,
                duration_seconds=time.monotonic() - started,
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            return ToolResult(
                ExecutionStatus.TIMEOUT,
                error=f"process timed out after {timeout_seconds:.3f}s",
                duration_seconds=time.monotonic() - started,
            )


def safe_path(root: Path, requested: str) -> Path:
    """Resolve a path and reject traversal outside the configured root."""

    base = root.resolve()
    candidate = (base / requested).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise ToolSecurityError("path escapes tool root") from exc
    return candidate
