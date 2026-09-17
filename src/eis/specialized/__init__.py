"""Specialized EIS agents and multi-agent coordination."""

from eis.specialized.models import (
    AgentAssignment,
    AgentChallenge,
    AgentKind,
    AgentSpec,
    CoordinationResult,
)
from eis.specialized.runtime import SPECS, AgentOrchestrator, DefaultAgentFactory

__all__ = [
    "SPECS",
    "AgentAssignment",
    "AgentChallenge",
    "AgentKind",
    "AgentOrchestrator",
    "AgentSpec",
    "CoordinationResult",
    "DefaultAgentFactory",
]
