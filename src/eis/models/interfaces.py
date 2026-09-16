"""Provider-neutral contracts and value objects for model execution."""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class Usage:
    """Normalized token and cost accounting returned by a model provider."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float | None = None
    currency: str | None = None

    def __post_init__(self) -> None:
        if min(self.input_tokens, self.output_tokens, self.total_tokens) < 0:
            raise ValueError("token counts cannot be negative")
        if self.estimated_cost is not None and self.estimated_cost < 0:
            raise ValueError("estimated_cost cannot be negative")


@dataclass(frozen=True, slots=True)
class ModelMetadata:
    """Capabilities and identity exposed by a provider model."""

    provider: str
    model: str
    context_window: int | None = None
    supports_structured_output: bool = False
    supports_tools: bool = False
    supports_streaming: bool = False
    supports_embeddings: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    parameters: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ToolCall:
    id: str
    name: str
    arguments: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    prompt: str
    system: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    tools: tuple[ToolDefinition, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    timeout: float | None = None
    trace_id: str | None = None


@dataclass(frozen=True, slots=True)
class StructuredGenerationRequest(GenerationRequest):
    schema: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GenerationResponse:
    text: str
    model: ModelMetadata
    usage: Usage
    tool_calls: tuple[ToolCall, ...] = ()
    raw: Any = None
    trace_id: str | None = None


@dataclass(frozen=True, slots=True)
class StructuredGenerationResponse:
    data: Mapping[str, Any]
    model: ModelMetadata
    usage: Usage
    raw: Any = None
    trace_id: str | None = None


@dataclass(frozen=True, slots=True)
class EmbeddingRequest:
    texts: tuple[str, ...]
    model: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    timeout: float | None = None
    trace_id: str | None = None


@dataclass(frozen=True, slots=True)
class EmbeddingResponse:
    vectors: tuple[tuple[float, ...], ...]
    model: ModelMetadata
    usage: Usage
    trace_id: str | None = None


@runtime_checkable
class Model(Protocol):
    """Stable interface consumed by EIS domains."""

    @property
    def metadata(self) -> ModelMetadata: ...

    async def generate(self, request: GenerationRequest) -> GenerationResponse: ...

    async def generate_structured(
        self, request: StructuredGenerationRequest
    ) -> StructuredGenerationResponse: ...

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse: ...

    async def stream(self, request: GenerationRequest) -> AsyncIterator[str]: ...


@runtime_checkable
class ModelProvider(Protocol):
    """Factory/registry boundary for concrete provider adapters."""

    @property
    def name(self) -> str: ...

    async def get_model(self, model: str | None = None) -> Model: ...


__all__ = [
    "EmbeddingRequest",
    "EmbeddingResponse",
    "GenerationRequest",
    "GenerationResponse",
    "Model",
    "ModelMetadata",
    "ModelProvider",
    "StructuredGenerationRequest",
    "StructuredGenerationResponse",
    "ToolCall",
    "ToolDefinition",
    "Usage",
]
