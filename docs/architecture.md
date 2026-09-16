# EIS Architecture

## Purpose
EIS is the central intelligence and controlled execution platform for Echowavs. The foundation separates stable contracts from replaceable infrastructure so model, retrieval, repository and execution technologies can evolve independently.

## Dependency direction

```text
SDK / entrypoints
       |
 orchestration
       |
 agents -> reasoning -> integrity -> knowledge/memory
       |                    |
 execution -> tools        model contracts -> provider adapters
       |
 security + observability (cross-cutting)
```

The core defines domain-neutral value objects and protocols. Concrete providers must depend inward on contracts, never the reverse.

## Domains

- **core** — shared value objects, runtime context, identities, lifecycle, events, results, hierarchy and errors; intentionally small and dependency-light.
- **configuration** — typed environment configuration and safe defaults; prevents configuration leaking through business code.
- **knowledge** — canonical, provenance-aware Echowavs knowledge and provider-neutral storage/ingestion contracts.
- **memory** — contextual and experiential memory distinct from canonical knowledge.
- **reasoning** — evidence-aware assessment and decision formation; keeps reasoning policy separate from model transport.
- **integrity** — claim taxonomy, evidence attribution, freshness, contradiction handling, confidence, uncertainty and Honest Intelligence invariants.
- **models** — provider-independent model requests, responses, tools, streaming, metadata, usage and reliability contracts.
- **agents** — capability-oriented agent lifecycle; agents orchestrate capabilities rather than owning infrastructure.
- **tools** — explicit external capabilities with permission boundaries.
- **execution** — controlled side effects; separates deciding what to do from actually doing it.
- **evaluation** — verification of outputs and actions against explicit expectations.
- **orchestration** — workflow coordination and lifecycle management.
- **security** — authorization, secret handling and policy enforcement.
- **observability** — structured logs, audit events, metrics and tracing contracts.
- **SDK** — stable public entry point for applications and future integrations.

## Model abstraction system

The Model Abstraction Layer is documented in [Model Abstraction](architecture/model-abstraction.md). EIS domains interact with `Model`, `ModelProvider`, `GenerationRequest`, `GenerationResponse`, structured-generation contracts, embedding contracts, normalized tool calls, model metadata and usage values. Concrete adapters are isolated under `eis.adapters.models`.

Phase 5 also adds `ReliableModel`, which centralizes request tracing, timeout handling, retry policy and normalized usage aggregation. Provider adapters translate API protocols only; they do not contain EIS business logic. `ModelRegistry` selects an injected provider from validated configuration.

The built-in `OpenAICompatibleModel` adapter can target multiple compatible hosted providers by configuration. `FakeModel` and `FakeModelProvider` provide deterministic test doubles. Additional providers can implement the same stable interfaces, including local model runtimes and providers with non-compatible APIs.

## Knowledge system

The canonical knowledge model is documented in [Knowledge System](architecture/knowledge-system.md). Knowledge is represented as immutable, versioned entities with explicit source provenance and relationships. Retrieval excludes invalidated current knowledge by default, preventing stale records from silently remaining authoritative. Storage and ingestion are protocols; the current local implementation is development-only.

## Memory system

The memory model is documented in [Memory System](architecture/memory-system.md). Memory records are classified as fact, observation, decision, assumption, inference, experience, failure, preference, or unknown, with explicit scope, provenance, confidence, relevance and lifecycle. Conflicting memories remain distinct; invalidated or superseded memories are excluded from normal retrieval. Most importantly, storing a memory never makes it authoritative organizational knowledge.

## Integrity system

The Integrity Engine is documented in [Integrity Engine](architecture/integrity-engine.md). It is a foundational dependency for future reasoning and agents. Claims are explicitly typed as facts, verified facts, observations, inferences, assumptions, opinions, proposals, unknowns, conflicting evidence, or uncertain. Evidence retains provenance and freshness metadata. Claim assessment exposes supporting and contradicting evidence, uncertainty, invalidators, and a bounded confidence basis. The engine does not silently resolve contradictions or manufacture support when evidence is absent.

Idea evaluation is an evidence-based assessment framework covering criterion-level findings, risks, dependencies, unknowns, and investigation paths. Its statuses are descriptive rather than approval/rejection decisions.

## Honest Intelligence

EIS must preserve the distinction between:

1. verified fact/evidence;
2. inference derived from evidence;
3. opinion or preference;
4. uncertainty or missing evidence;
5. proposed action.

The Integrity Engine turns these principles into enforceable domain contracts instead of relying only on prompts. Future model-generated claims must pass through these boundaries before becoming trusted inputs to reasoning or agents.

## Provider neutrality

The `models` domain owns all model-facing contracts. No domain module should import an LLM provider SDK. Concrete provider adapters depend on `eis.models`, never the reverse. The same boundary applies to knowledge, memory and repository providers. Future adapters can target local models, hosted APIs, multiple embedding engines, SQL/vector stores, GitHub, GitLab, or other repository systems without changing domain contracts.

## Execution safety

Reasoning produces decisions; execution applies approved actions. Tool calls and side effects must pass through security and execution boundaries. Later phases should introduce explicit dry-run, approval, idempotency and rollback semantics rather than allowing agents to execute arbitrary code.

## Current scope

Phase 1 contains the runtime foundation. Phase 2 adds canonical knowledge models, provenance, relationships, versioning, invalidation, provider-neutral repository and ingestion interfaces, and a local development store. Phase 3 adds first-class memory models, lifecycle-aware local retrieval, confidence/relevance metadata, conflict and uncertainty handling, and summarization interfaces. Phase 4 adds the deterministic Integrity Engine, explicit claim/evidence models, contradiction and freshness checks, HonestResponse/IdeaEvaluation structures, confidence calibration interfaces, and hallucination-focused tests. Phase 5 adds provider-independent model contracts, configuration-driven selection, a concrete OpenAI-compatible HTTP adapter, deterministic fakes, structured provider errors, retry/timeout handling, tracing and usage aggregation. Advanced agent behavior, autonomous execution and provider-specific business logic remain outside this phase.
