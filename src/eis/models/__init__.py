"""Provider-independent model abstractions."""

from eis.models.errors import (
    ModelConfigurationError,
    ModelError,
    ModelRateLimitError,
    ModelTimeoutError,
    ModelUnavailableError,
    ModelValidationError,
)
from eis.models.interfaces import (
    GenerationRequest,
    GenerationResponse,
    Model,
    ModelMetadata,
    ModelProvider,
    StructuredGenerationRequest,
    StructuredGenerationResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ToolCall,
    ToolDefinition,
    Usage,
)
from eis.models.policy import RetryPolicy

__all__ = [
    "EmbeddingRequest",
    "EmbeddingResponse",
    "GenerationRequest",
    "GenerationResponse",
    "Model",
    "ModelConfigurationError",
    "ModelError",
    "ModelMetadata",
    "ModelProvider",
    "ModelRateLimitError",
    "ModelTimeoutError",
    "ModelUnavailableError",
    "ModelValidationError",
    "RetryPolicy",
    "StructuredGenerationRequest",
    "StructuredGenerationResponse",
    "ToolCall",
    "ToolDefinition",
    "Usage",
]
