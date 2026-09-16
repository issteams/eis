"""Configuration-driven provider selection."""

from __future__ import annotations

from collections.abc import Mapping

from eis.config.settings import Settings
from eis.models.errors import ModelConfigurationError
from eis.models.fakes import FakeModelProvider
from eis.models.interfaces import Model, ModelProvider
from eis.models.policy import RetryPolicy
from eis.models.runtime import ReliableModel


class ModelRegistry:
    """Resolves configured provider names without leaking provider details into EIS."""

    def __init__(self, providers: Mapping[str, ModelProvider]) -> None:
        self._providers = dict(providers)

    async def resolve(self, settings: Settings) -> Model:
        provider_name = settings.model_provider.strip().lower()
        if not provider_name or provider_name == "none":
            raise ModelConfigurationError("no model provider is configured")
        try:
            provider = self._providers[provider_name]
        except KeyError as exc:
            raise ModelConfigurationError(
                f"unknown model provider: {provider_name}"
            ) from exc
        model = await provider.get_model(settings.model_name or None)
        return ReliableModel(
            model,
            retry_policy=RetryPolicy(max_attempts=settings.model_max_attempts),
        )


def default_registry() -> ModelRegistry:
    """Build the minimal built-in registry; external adapters can be injected by applications."""
    return ModelRegistry({FakeModelProvider.name: FakeModelProvider()})
