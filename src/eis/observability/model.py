"""Instrumentation adapter for the provider-neutral model boundary."""

from __future__ import annotations

import time

from eis.models.interfaces import (
    EmbeddingRequest,
    EmbeddingResponse,
    GenerationRequest,
    GenerationResponse,
    Model,
    ModelMetadata,
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
    def metadata(self) -> ModelMetadata:
        return self._model.metadata

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        started = time.monotonic()
        try:
            response = await self._model.generate(request)
        except Exception:
            self._observability.metrics.increment(
                "eis_model_failures_total", operation="generate"
            )
            raise
        self._record(response, time.monotonic() - started)
        return response

    async def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResponse:
        started = time.monotonic()
        try:
            response = await self._model.generate_structured(request)
        except Exception:
            self._observability.metrics.increment(
                "eis_model_failures_total", operation="generate_structured"
            )
            raise
        self._record(response, time.monotonic() - started)
        return response

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        started = time.monotonic()
        try:
            response = await self._model.embed(request)
        except Exception:
            self._observability.metrics.increment("eis_model_failures_total", operation="embed")
            raise
        self._record(response, time.monotonic() - started)
        return response

    def _record(
        self,
        response: GenerationResponse | StructuredGenerationResponse | EmbeddingResponse,
        latency_seconds: float,
    ) -> None:
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
                latency_seconds=latency_seconds,
                success=True,
            )
        )

    def stream(self, request: GenerationRequest):
        return self._model.stream(request)


__all__ = ["InstrumentedModel"]
