"""Protocols that isolate tools from the execution environment."""

from __future__ import annotations

from typing import Any, Protocol

from eis.tools.models import AuditEvent, ToolDefinition, ToolRequest, ToolResult


class Tool(Protocol):
    """Agent-facing secure tool contract."""

    definition: ToolDefinition

    async def execute(self, request: ToolRequest) -> ToolResult: ...


class ExecutionBackend(Protocol):
    """Environment boundary replaceable by a future sandbox/container backend."""

    async def run(
        self,
        operation: str,
        arguments: dict[str, Any],
        timeout_seconds: float,
    ) -> ToolResult: ...


class AuditSink(Protocol):
    def record(self, event: AuditEvent) -> None: ...


class PolicyAuthorizer(Protocol):
    def authorize(self, request: ToolRequest, definition: ToolDefinition) -> None: ...
