# EIS Core Runtime and Identity

Phase 1 establishes the stable runtime substrate used by every future EIS component.

## Runtime

`EISRuntime` owns typed settings, EIS instance identity, lifecycle state, local event dispatch, and request-context creation. Its lifecycle is `CREATED -> STARTED -> STOPPED`; stopped runtimes cannot be restarted.

## Identity hierarchy

```text
Echowavs
  -> Division
  -> Product
  -> Project
  -> Repository
  -> Task
```

The hierarchy is represented with immutable identity value objects and `OrganizationHierarchy`. Only company scope is required; narrower scopes are optional so a task can be represented at the appropriate organizational level.

Core logic does not name any specific Echowavs product. Organization-defined names and relationships belong in `config.organization` and can later be populated from canonical organizational knowledge.

## Execution context

`EISContext` carries hierarchy, session identity, request identity, correlation ID and metadata. Child contexts retain correlation identity and merge metadata, creating a stable context propagation mechanism for future agents, tools, reasoning, execution and observability.

## Events

`EISEvent` is an infrastructure-neutral structured event with event type, event ID, UTC-aware timestamp, correlation ID and structured payload. Phase 1 only provides local subscription/dispatch; durable event infrastructure is intentionally deferred.

## Results

`Result[T]` and `Status` provide explicit operation outcomes. Success requires a successful status and no error; failures carry a non-empty error message. This creates a stable boundary for future provider and execution adapters.

## Configuration

Runtime settings use the `EIS_` environment-variable prefix and support development, testing, staging and production environments. Provider settings remain `none` by default. Organization configuration is separate from runtime settings so products and projects are data, not hard-coded behavior.

## Independence guarantees

Phase 1 core runtime and identity code has no LLM, embedding, vector database, repository SDK, network service, shell execution or cloud-provider dependency. Future infrastructure is connected through protocols/adapters rather than imported into core.
