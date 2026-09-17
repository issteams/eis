"""Specialized EIS agents and multi-agent coordination."""

from eis.specialized.models import (
    AgentAssignment,
    AgentChallenge,
    AgentKind,
    AgentSpec,
    CoordinationResult,
)
from eis.specialized.runtime import AgentOrchestrator, DefaultAgentFactory, SPECS

__all__ = [
    "AgentAssignment",
    "AgentChallenge",
    "AgentKind",
    "AgentOrchestrator",
    "AgentSpec",
    "CoordinationResult",
    "DefaultAgentFactory",
    "SPECS",
]
