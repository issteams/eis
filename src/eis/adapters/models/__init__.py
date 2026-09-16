"""Concrete model provider adapters."""

from eis.adapters.models.openai_compatible import OpenAICompatibleModel
from eis.adapters.models.providers import OpenAICompatibleProvider

__all__ = ["OpenAICompatibleModel", "OpenAICompatibleProvider"]
