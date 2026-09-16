# EIS Memory System

## Purpose

Memory is a first-class subsystem for retaining useful experience and context across sessions, tasks, projects, agents, and organizational activity. It is deliberately separate from organizational knowledge.

## Memory scopes

- **Organizational** — memories about company activity and recurring organizational context.
- **Project** — project-specific experience and context.
- **Task** — short-lived task context and outcomes.
- **Agent** — agent-specific experience.
- **Session** — one execution/session's context.
- **Episodic** — events and experiences that happened at a point in time.
- **Decision** — recorded decisions and their context.
- **Failure** — failed attempts, causes, and lessons.

## Memory kinds

Every record is classified as one of:

`FACT`, `OBSERVATION`, `DECISION`, `ASSUMPTION`, `INFERENCE`, `EXPERIENCE`, `FAILURE`, `PREFERENCE`, or `UNKNOWN`.

Classification prevents EIS from flattening observations, assumptions, and inferences into facts.

## Record properties

A `MemoryRecord` contains:

- stable ID
- scope and kind
- content
- provenance
- creation and observation timestamps
- confidence
- relevance
- lifecycle status
- invalidation information
- optional superseded record ID
- extensible metadata

Confidence expresses how strongly the memory is supported. Relevance expresses retrieval usefulness. Neither value makes a memory authoritative.

## Provenance

Memory reuses the Phase 2 provenance model. Every record has a source and capture metadata. This allows EIS to distinguish what was observed from what was inferred later.

## Lifecycle

Active memories can become **invalidated** when their supporting information is no longer valid, or **superseded** when a newer memory replaces their operational relevance. Historical records are retained by the local implementation and can only be requested explicitly with `include_inactive=True`.

## Conflicting memories

Conflicting memories are retained as separate records. The memory layer does not silently select a winner or rewrite one record into another. Retrieval exposes confidence and provenance so a higher-level reasoning system can evaluate the conflict.

## Stale memories

Age alone does not prove that a memory is false. A memory becomes inactive only through explicit invalidation or supersession. This avoids silently discarding historical experience while preventing invalidated memories from normal retrieval.

## Uncertain memories

Uncertain information remains uncertain. `UNKNOWN`, `ASSUMPTION`, and `INFERENCE` are preserved as distinct types, and confidence is retained during retrieval.

## Knowledge boundary

**Stored memory is not authoritative organizational knowledge.** There is no implicit promotion path in the memory repository. A future knowledge-promotion workflow must explicitly evaluate evidence, provenance, conflicts, and authority before creating or updating a `KnowledgeEntity`.

## Interfaces

`MemoryRepository` defines storage, retrieval, update, invalidation, supersession, and deletion without choosing a database.

`MemorySummarizer` defines an asynchronous summarization boundary without coupling EIS to an LLM provider. No summarization implementation is included in this phase.

`LocalMemoryRepository` is intentionally deterministic and in-memory for development and tests.
