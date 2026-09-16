"""Provider factories for concrete model adapters."""

from __future__ import annotations

from eis.config.settings import Settings
from eis.models.interfaces import Model, ModelProvider
from eis.adapters.models.openai_compatible import OpenAICompatibleModel


class OpenAICompatibleProvider:
    """Factory for OpenAI-compatible hosted endpoints."""

    def __init__(self, settings: Settings, *, name: str | None = None) -> None:
        self._settings = settings
        self._name = name or settings.model_provider

    @property
    def name(self) -> str:
        return self._name

    async def get_model(self, model: str | None = None) -> Model:
        return OpenAICompatibleModel(
            provider=self._name,
            base_url=self._settings.model_base_url,
            api_key=self._settings.model_api_key,
            model=model or self._settings.model_name,
            timeout=self._settings.model_timeout,
        )
