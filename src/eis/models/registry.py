"""Configuration-driven provider selection."""

from __future__ import annotations

from collections.abc import Mapping

from eis.adapters.models import CloudflareProvider, OpenAICompatibleProvider
from eis.config.settings import Settings, get_settings
from eis.models.errors import ModelConfigurationError
from eis.models.fakes import FakeModelProvider
from eis.models.interfaces import Model, ModelProvider
from eis.models.policy import RetryPolicy
from eis.models.runtime import ReliableModel


_OPENAI_COMPATIBLE_PROVIDERS = frozenset({"openrouter"})


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
            raise ModelConfigurationError(f"unknown model provider: {provider_name}") from exc
        model = await provider.get_model(settings.model_name or None)
        return ReliableModel(
            model,
            retry_policy=RetryPolicy(max_attempts=settings.model_max_attempts),
        )


def default_registry(settings: Settings | None = None) -> ModelRegistry:
    """Build the built-in registry from the configured model provider.

    The registry always keeps the deterministic fake provider for local/testing use.
    Supported external providers are wired only when selected through EIS settings.
    """
    resolved_settings = settings or get_settings()
    providers: dict[str, ModelProvider] = {FakeModelProvider.name: FakeModelProvider()}
    provider_name = resolved_settings.model_provider.strip().lower()

    if provider_name in _OPENAI_COMPATIBLE_PROVIDERS:
        if not resolved_settings.model_base_url:
            raise ModelConfigurationError(
                f"model_base_url is required for provider: {provider_name}"
            )
        if not resolved_settings.model_api_key:
            raise ModelConfigurationError(
                f"model_api_key is required for provider: {provider_name}"
            )
        if not resolved_settings.model_name:
            raise ModelConfigurationError(f"model_name is required for provider: {provider_name}")
        providers[provider_name] = OpenAICompatibleProvider(
            resolved_settings,
            name=provider_name,
        )
    elif provider_name == "cloudflare":
        if not resolved_settings.cloudflare_account_id:
            raise ModelConfigurationError("cloudflare_account_id is required for provider: cloudflare")
        if not resolved_settings.model_api_key:
            raise ModelConfigurationError("model_api_key is required for provider: cloudflare")
        if not resolved_settings.model_name:
            raise ModelConfigurationError("model_name is required for provider: cloudflare")
        providers[provider_name] = CloudflareProvider(resolved_settings)

    return ModelRegistry(providers)
