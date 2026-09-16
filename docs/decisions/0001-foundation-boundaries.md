# ADR 0001 — Foundation boundaries and Honest Intelligence

**Status:** Accepted  
**Date:** 2026-09-16

## Context

EIS is intended to grow from a knowledge and engineering assistant into a controlled autonomous intelligence platform. Early coupling to one model, vector database, repository provider, or execution mechanism would make later changes expensive and could weaken safety boundaries.

## Decisions

### 1. Protocol-first architecture
Stable interfaces live in `core` and domain `protocols.py` modules. Implementations are injected later.

**Why:** domain behavior remains testable without infrastructure and provider replacement does not require rewriting the core.

### 2. Honest Intelligence is architectural
Evidence, decisions, uncertainty and proposed actions are explicit data concepts. Integrity has its own boundary.

**Why:** honesty cannot safely depend only on prompt wording. The system needs inspectable invariants and provenance.

### 3. Knowledge and memory are separate
Canonical organizational knowledge is distinct from transient/session/agent memory.

**Why:** not every remembered interaction should become organizational truth.

### 4. Decision and execution are separate
Reasoning may recommend an action; execution is a separate controlled capability.

**Why:** this creates a future approval, policy, dry-run and audit boundary.

### 5. No provider SDK in core
LLM, embedding, vector store and repository implementations are future adapters.

**Why:** local/cloud models and infrastructure can coexist and be replaced independently.

### 6. Explicit unimplemented state
The initial client reports provider capabilities as `none` rather than supplying fake implementations.

**Why:** a system whose central principle is honesty must never represent scaffolding as working intelligence.
