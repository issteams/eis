# Core Principles

## 1. Evidence before confidence

Important claims should have traceable evidence. EIS keeps provenance and integrity boundaries explicit.

## 2. Explicit over implicit

Agents, tools, evaluators, engineers, orchestrators, and external capabilities are registered or injected explicitly. EIS does not silently select a provider or capability.

## 3. Controlled side effects

Reasoning and planning are separated from operations that can change external state. Tool and execution boundaries are explicit.

## 4. Verification is a first-class concern

Verification is represented by dedicated evaluation and integrity components. Performance work must not remove verification merely to reduce latency or cost.

## 5. Provider independence

Domain code depends on protocols and stable abstractions rather than a specific LLM, embedding service, repository provider, or infrastructure vendor.

## 6. Auditable behavior

SDK actions and production operations expose audit/observability data appropriate to their boundary.

## 7. Deterministic infrastructure where practical

Routing, scheduling, retrieval selection, context budgeting, retries, and other infrastructure behaviors use explicit rules so they can be tested and measured.

## 8. Safe degradation

When an optional integration is unavailable, the system should fail explicitly or degrade within a defined boundary rather than inventing a result.

## 9. Documentation follows implementation

Documentation describes behavior that exists in the repository. Future architecture is labeled as future architecture.
