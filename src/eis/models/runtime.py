"""Cross-provider reliability, tracing and usage orchestration."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from time import monotonic
from typing import Any, TypeVar

from eis.models.errors import ModelError, ModelTimeoutError
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
from eis.models.policy import RetryPolicy

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ModelTrace:
    trace_id: str
    provider: str
    model: str
    operation: str
    duration_ms: float
    attempts: int


@dataclass(frozen=True, slots=True)
class UsageLedger:
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0

    def record(
        self,
        response: GenerationResponse | StructuredGenerationResponse | EmbeddingResponse,
    ) -> UsageLedger:
        usage = response.usage
        return UsageLedger(
            requests=self.requests + 1,
            input_tokens=self.input_tokens + usage.input_tokens,
            output_tokens=self.output_tokens + usage.output_tokens,
            estimated_cost=self.estimated_cost + (usage.estimated_cost or 0.0),
        )


class ReliableModel:
    """Adds tracing, timeout and retry behavior without changing provider adapters."""

    def __init__(self, model: Model, *, retry_policy: RetryPolicy | None = None) -> None:
        self._model = model
        self._policy = retry_policy or RetryPolicy()
        self._traces: list[ModelTrace] = []
        self._usage = UsageLedger()

    @property
    def metadata(self) -> ModelMetadata:
        return self._model.metadata

    @property
    def traces(self) -> tuple[ModelTrace, ...]:
        return tuple(self._traces)

    @property
    def usage(self) -> UsageLedger:
        return self._usage

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        response = await self._call("generate", request, self._model.generate)
        self._usage = self._usage.record(response)
        return response

    async def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResponse:
        response = await self._call("generate_structured", request, self._model.generate_structured)
        self._usage = self._usage.record(response)
        return response

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        response = await self._call("embed", request, self._model.embed)
        self._usage = self._usage.record(response)
        return response

    async def stream(self, request: GenerationRequest) -> AsyncIterator[str]:
        trace_id = request.trace_id or uuid.uuid4().hex
        started = monotonic()
        attempts = 0
        timeout = request.timeout
        while True:
            attempts += 1
            try:
                iterator = self._model.stream(request)
                async for chunk in self._stream_with_timeout(iterator, timeout):
                    yield chunk
                self._traces.append(
                    ModelTrace(
                        trace_id,
                        self.metadata.provider,
                        self.metadata.model,
                        "stream",
                        (monotonic() - started) * 1000,
                        attempts,
                    )
                )
                return
            except ModelError as exc:
                if not exc.retryable or attempts >= self._policy.max_attempts:
                    raise
                await asyncio.sleep(self._policy.delay(attempts))

    async def _call(
        self,
        operation: str,
        request: Any,
        function: Callable[[Any], Awaitable[T]],
    ) -> T:
        trace_id = getattr(request, "trace_id", None) or uuid.uuid4().hex
        timeout = getattr(request, "timeout", None)
        started = monotonic()
        attempts = 0
        while True:
            attempts += 1
            try:
                result = await asyncio.wait_for(function(request), timeout=timeout)
                self._traces.append(
                    ModelTrace(
                        trace_id,
                        self.metadata.provider,
                        self.metadata.model,
                        operation,
                        (monotonic() - started) * 1000,
                        attempts,
                    )
                )
                return result
            except TimeoutError as exc:
                if attempts >= self._policy.max_attempts:
                    raise ModelTimeoutError(
                        f"{operation} timed out",
                        provider=self.metadata.provider,
                        retryable=False,
                    ) from exc
                await asyncio.sleep(self._policy.delay(attempts))
            except ModelError as exc:
                if not exc.retryable or attempts >= self._policy.max_attempts:
                    raise
                await asyncio.sleep(self._policy.delay(attempts))

    @staticmethod
    async def _stream_with_timeout(
        iterator: AsyncIterator[str], timeout: float | None
    ) -> AsyncIterator[str]:
        if timeout is None:
            async for chunk in iterator:
                yield chunk
            return
        while True:
            try:
                yield await asyncio.wait_for(iterator.__anext__(), timeout=timeout)
            except StopAsyncIteration:
                return
