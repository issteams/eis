"""Instrumentation adapter for the provider-neutral model boundary."""

from __future__ import annotations

import time
from typing import Any

from eis.models.interfaces import (
    EmbeddingRequest,
    EmbeddingResponse,
    GenerationRequest,
    GenerationResponse,
    Model,
    StructuredGenerationRequest,
    StructuredGenerationResponse,
)
from eis.observability.models import ModelUsageMetric
from eis.observability.runtime import Observability


class InstrumentedModel:
    """Wrap a model without changing the model provider abstraction."""

    def __init__(self, model: Model, observability: Observability) -> None:
        self._model = model
        self._observability = observability

    @property
    def metadata(self) -> Any:
        return self._model.metadata

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        return await self._run("generate", request, self._model.generate)

    async def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResponse:
        return await self._run("generate_structured", request, self._model.generate_structured)

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        return await self._run("embed", request, self._model.embed)

    async def _run(self, operation: str, request: Any, call: Any) -> Any:
        started = time.monotonic()
        try:
            response = await call(request)
            usage = response.usage
            self._observability.record_model_usage(
                ModelUsageMetric(
                    provider=response.model.provider,
                    model=response.model.model,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    total_tokens=usage.total_tokens,
                    estimated_cost=usage.estimated_cost,
                    currency=usage.currency,
                    latency_seconds=time.monotonic() - started,
                    success=True,
                )
            )
            return response
        except Exception:
            self._observability.metrics.increment("eis_model_failures_total", operation=operation)
            raise

    def stream(self, request: GenerationRequest):
        return self._model.stream(request)


__all__ = ["InstrumentedModel"]
