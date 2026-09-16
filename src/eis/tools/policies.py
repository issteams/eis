"""Security policy enforcement for tool execution."""

from __future__ import annotations

from dataclasses import dataclass

from eis.tools.models import ExecutionPolicy, ToolDefinition, ToolRequest


class ToolSecurityError(PermissionError):
    """Raised when a tool request violates the execution security boundary."""


@dataclass(frozen=True, slots=True)
class SecurityPolicy:
    """Central policy gate with conservative defaults."""

    allow_high_risk: bool = False
    allow_controlled_write: bool = True
    allow_safe_write: bool = True
    allow_read_only: bool = True

    def authorize(self, request: ToolRequest, definition: ToolDefinition) -> None:
        if definition.execution_policy is ExecutionPolicy.PROHIBITED:
            raise ToolSecurityError(f"tool is prohibited: {definition.name}")
        allowed = {
            ExecutionPolicy.READ_ONLY: self.allow_read_only,
            ExecutionPolicy.SAFE_WRITE: self.allow_safe_write,
            ExecutionPolicy.CONTROLLED_WRITE: self.allow_controlled_write,
            ExecutionPolicy.HIGH_RISK: self.allow_high_risk,
            ExecutionPolicy.PROHIBITED: False,
        }[definition.execution_policy]
        if not allowed:
            raise ToolSecurityError(f"execution policy denied: {definition.execution_policy.value}")


@dataclass(frozen=True, slots=True)
class ExecutionLimits:
    max_output_bytes: int = 1_000_000
    max_arguments: int = 100
    max_timeout_seconds: float = 120.0

    def validate(self, definition: ToolDefinition, request: ToolRequest) -> None:
        if len(request.arguments) > self.max_arguments:
            raise ToolSecurityError("too many tool arguments")
        if definition.timeout_seconds <= 0 or definition.timeout_seconds > self.max_timeout_seconds:
            raise ToolSecurityError("tool timeout exceeds execution limit")
