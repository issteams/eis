"""Provider-independent model abstractions."""

from eis.models.errors import (
    ModelConfigurationError,
    ModelError,
    ModelRateLimitError,
    ModelTimeoutError,
    ModelUnavailableError,
    ModelValidationError,
)
from eis.models.fakes import FakeModel, FakeModelProvider
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
    ToolDefinition,
    Usage,
)
from eis.models.policy import RetryPolicy
from eis.models.registry import ModelRegistry, default_registry
from eis.models.runtime import ModelTrace, ReliableModel, UsageLedger

__all__ = [
    "EmbeddingRequest",
    "EmbeddingResponse",
    "FakeModel",
    "FakeModelProvider",
    "GenerationRequest",
    "GenerationResponse",
    "Model",
    "ModelConfigurationError",
    "ModelError",
    "ModelMetadata",
    "ModelProvider",
    "ModelRateLimitError",
    "ModelRegistry",
    "ModelTimeoutError",
    "ModelTrace",
    "ModelUnavailableError",
    "ModelValidationError",
    "ReliableModel",
    "RetryPolicy",
    "StructuredGenerationRequest",
    "StructuredGenerationResponse",
    "ToolCall",
    "ToolDefinition",
    "Usage",
    "UsageLedger",
    "default_registry",
]
