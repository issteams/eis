"""Concrete model provider adapters."""

from eis.adapters.models.cloudflare import CloudflareModel
from eis.adapters.models.cloudflare_provider import CloudflareProvider
from eis.adapters.models.openai_compatible import OpenAICompatibleModel
from eis.adapters.models.providers import OpenAICompatibleProvider

__all__ = [
    "CloudflareModel",
    "CloudflareProvider",
    "OpenAICompatibleModel",
    "OpenAICompatibleProvider",
]
