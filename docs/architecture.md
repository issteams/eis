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
 execution -> tools        providers/adapters
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
- **integrity** — provenance, evidence validation and honesty invariants; this is the architectural home of the Honest Intelligence principle.
- **agents** — capability-oriented agent lifecycle; agents orchestrate capabilities rather than owning infrastructure.
- **tools** — explicit external capabilities with permission boundaries.
- **execution** — controlled side effects; separates deciding what to do from actually doing it.
- **evaluation** — verification of outputs and actions against explicit expectations.
- **orchestration** — workflow coordination and lifecycle management.
- **security** — authorization, secret handling and policy enforcement.
- **observability** — structured logs, audit events, metrics and tracing contracts.
- **SDK** — stable public entry point for applications and future integrations.

## Knowledge system

The canonical knowledge model is documented in [Knowledge System](architecture/knowledge-system.md). Knowledge is represented as immutable, versioned entities with explicit source provenance and relationships. Retrieval excludes invalidated current knowledge by default, preventing stale records from silently remaining authoritative. Storage and ingestion are protocols; the current local implementation is development-only.

## Memory system

The memory model is documented in [Memory System](architecture/memory-system.md). Memory records are classified as fact, observation, decision, assumption, inference, experience, failure, preference, or unknown, with explicit scope, provenance, confidence, relevance and lifecycle. Conflicting memories remain distinct; invalidated or superseded memories are excluded from normal retrieval. Most importantly, storing a memory never makes it authoritative organizational knowledge.

## Honest Intelligence

EIS must preserve the distinction between:

1. verified fact/evidence;
2. inference derived from evidence;
3. opinion or preference;
4. uncertainty or missing evidence;
5. proposed action.

A future reasoning implementation must not silently convert uncertainty into confidence. Integrity is therefore a first-class boundary rather than a prompt-only convention.

## Provider neutrality

`Model`, `Embedder`, `KnowledgeStore`, and `Repository` are protocols. Memory storage is also defined by `MemoryRepository`, while summarization is isolated behind `MemorySummarizer`. No domain module imports an LLM SDK, vector database client, or Git provider SDK. Future adapters can target local models, hosted APIs, multiple embedding engines, SQL/vector stores, GitHub, GitLab, or other repository systems without changing the domain contracts.

## Execution safety

Reasoning produces decisions; execution applies approved actions. Tool calls and side effects must pass through security and execution boundaries. Later phases should introduce explicit dry-run, approval, idempotency and rollback semantics rather than allowing agents to execute arbitrary code.

## Current scope

Phase 1 contains the runtime foundation. Phase 2 adds canonical knowledge models, provenance, relationships, versioning, invalidation, provider-neutral repository and ingestion interfaces, and a local development store. Phase 3 adds first-class memory models, lifecycle-aware local retrieval, confidence/relevance metadata, conflict and uncertainty handling, and summarization interfaces. No advanced AI behavior, LLM integration, vector database, external source connector, or autonomous memory promotion is implemented yet.
