# Model Abstraction Layer

Phase 5 establishes the provider boundary for EIS. Core domains consume `Model` and `ModelProvider` contracts from `eis.models`; concrete providers live under `eis.adapters.models`.

## Stable contracts

The abstraction represents:

- text generation through `GenerationRequest` / `GenerationResponse`
- structured generation through `StructuredGenerationRequest` / `StructuredGenerationResponse`
- embeddings through `EmbeddingRequest` / `EmbeddingResponse`
- tool definitions and normalized `ToolCall` values
- streaming through an async iterator
- model capabilities through `ModelMetadata`
- normalized token and cost accounting through `Usage`

Provider SDK types must not cross this boundary.

## Provider selection

`Settings` selects `model_provider`, `model_name`, endpoint, timeout, and retry attempts through `EIS_*` environment variables. `ModelRegistry` maps the configured provider name to an injected `ModelProvider` implementation.

The built-in HTTP adapter is `OpenAICompatibleModel`. One adapter can serve multiple compatible providers by configuration rather than by changing EIS domain code. Applications can register additional providers, including local models or providers with different APIs, without changing the stable model contracts.

## Reliability boundary

`ReliableModel` wraps a provider model and owns cross-provider reliability concerns:

- request tracing
- timeout handling
- retry policy
- retryable provider failures
- normalized usage aggregation

Provider adapters translate API requests and responses. They do not decide business outcomes, evaluate ideas, modify knowledge, or perform agent reasoning.

## Errors

Model operations use structured errors:

- `ModelConfigurationError`
- `ModelValidationError`
- `ModelTimeoutError`
- `ModelRateLimitError`
- `ModelUnavailableError`

Rate limits preserve an optional `retry_after` value. Retryability is explicit rather than inferred by callers.

## Testing

`FakeModel` and `FakeModelProvider` provide deterministic implementations for unit tests. EIS tests should prefer these fakes over network calls. Provider-specific integration tests belong in adapter-level test suites and must never become a dependency of the core test suite.

## Integrity relationship

Model output is untrusted model output. Phase 4's Integrity Engine remains the boundary for evidence, confidence, uncertainty, contradiction handling, and honest assessment. The model layer provides capabilities; it does not make model output authoritative knowledge.
