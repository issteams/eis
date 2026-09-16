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
)
from eis.tools.policies import ExecutionLimits, SecurityPolicy, ToolSecurityError
from eis.tools.protocols import AuditSink, ExecutionBackend, PolicyAuthorizer


class ToolExecutionError(RuntimeError):
    """Raised for malformed or failed tool execution."""


@dataclass(slots=True)
class InMemoryAuditSink:
    events: list[AuditEvent] = field(default_factory=list)

    def record(self, event: AuditEvent) -> None:
        self.events.append(event)


class SecureExecutor:
    """Executes registered tools only after policy, permission, and limit checks."""

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
        definition = self._definition(request.tool)
        status = ExecutionStatus.FAILED
        error: str | None = None
        result = ToolResult(ExecutionStatus.FAILED, request_id=request.request_id)
        try:
            self._limits.validate(definition, request)
            self._policy.authorize(request, definition)
            tool = self._tools[request.tool]
            result = await asyncio.wait_for(
                tool.execute(request), timeout=definition.timeout_seconds
            )
            status = result.status
            return result
        except TimeoutError:
            status = ExecutionStatus.TIMEOUT
            error = f"tool timed out after {definition.timeout_seconds:.3f}s"
            return ToolResult(
                status, error=error, request_id=request.request_id
            )
        except (ToolSecurityError, PermissionError) as exc:
            status = ExecutionStatus.DENIED
            error = str(exc)
            return ToolResult(status, error=error, request_id=request.request_id)
        except Exception as exc:
            status = ExecutionStatus.FAILED
            error = str(exc)
            return ToolResult(status, error=error, request_id=request.request_id)
        finally:
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


@dataclass(frozen=True, slots=True)
class LocalSubprocessBackend:
    """Small subprocess backend; callers must pass an already validated argv list."""

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
        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
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
