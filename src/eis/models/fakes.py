"""Deterministic fake provider implementations for tests and local development."""

from __future__ import annotations

from collections.abc import AsyncIterator

from eis.models.interfaces import (
    EmbeddingRequest,
    EmbeddingResponse,
    GenerationRequest,
    GenerationResponse,
    Model,
    ModelMetadata,
    ModelProvider,
    StructuredGenerationRequest,
    StructuredGenerationResponse,
    ToolCall,
    Usage,
)


class FakeModel:
    """A configurable model with no network or provider SDK dependency."""

    def __init__(self, name: str = "fake-model") -> None:
        self._metadata = ModelMetadata(
            provider="fake",
            model=name,
            context_window=8192,
            supports_structured_output=True,
            supports_tools=True,
            supports_streaming=True,
            supports_embeddings=True,
        )
        self.failures = 0
        self.response_text = "fake response"
        self.tool_calls: tuple[ToolCall, ...] = ()
        self.usage = Usage(input_tokens=3, output_tokens=2, total_tokens=5)

    @property
    def metadata(self) -> ModelMetadata:
        return self._metadata

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        self._maybe_fail()
        return GenerationResponse(self.response_text, self._metadata, self.usage, self.tool_calls, trace_id=request.trace_id)

    async def generate_structured(self, request: StructuredGenerationRequest) -> StructuredGenerationResponse:
        self._maybe_fail()
        return StructuredGenerationResponse({"response": self.response_text}, self._metadata, self.usage, trace_id=request.trace_id)

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        self._maybe_fail()
        vectors = tuple((float(index), 1.0) for index, _ in enumerate(request.texts))
        return EmbeddingResponse(vectors, self._metadata, self.usage, request.trace_id)

    async def stream(self, request: GenerationRequest) -> AsyncIterator[str]:
        self._maybe_fail()
        for chunk in self.response_text.split():
            yield chunk

    def _maybe_fail(self) -> None:
        if self.failures > 0:
            self.failures -= 1
            from eis.models.errors import ModelUnavailableError

            raise ModelUnavailableError("fake transient failure", provider="fake")


class FakeModelProvider:
    """Provider registry implementation used by tests."""

    name = "fake"

    def __init__(self, model: FakeModel | None = None) -> None:
        self.model = model or FakeModel()

    async def get_model(self, model: str | None = None) -> Model:
        return self.model
