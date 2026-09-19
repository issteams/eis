"""Cloudflare provider factory."""

from __future__ import annotations

from eis.adapters.models.cloudflare import CloudflareModel
from eis.config.settings import Settings
from eis.models.interfaces import Model


class CloudflareProvider:
    """Factory for Cloudflare Workers AI models."""

    name = "cloudflare"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def get_model(self, model: str | None = None) -> Model:
        return CloudflareModel(
            account_id=self._settings.cloudflare_account_id,
            api_key=self._settings.model_api_key,
            model=model or self._settings.model_name,
            timeout=self._settings.model_timeout,
            gateway_id=self._settings.cloudflare_gateway_id or None,
        )
