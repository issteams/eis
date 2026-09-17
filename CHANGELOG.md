# Changelog

All notable EIS changes are recorded here.

## [1.0.0] — Release candidate

EIS 1.0.0 consolidates the production-oriented foundation and public Python SDK developed through the architecture phases.

### Added

- Provider-independent model contracts for generation, structured generation, embeddings, tool calls, streaming, metadata, usage, and cost.
- Organizational knowledge and memory boundaries with traceability primitives.
- Evidence-aware context retrieval and integrity controls.
- Agent, tool, execution, evaluation, orchestration, and engineering contracts.
- Security, authorization, governance, observability, health, recovery, and durable workflow infrastructure.
- Controlled integrations through explicit adapters rather than hidden provider coupling.
- Performance controls including bounded caching, context optimization, model routing, scheduling, batching, retry optimization, and retrieval optimization.
- Deterministic performance benchmarks.
- Production documentation, architecture decision records, development guidance, and release gates.
- Public SDK end-to-end smoke coverage.
- Release-time packaging and dependency-audit validation in CI.

### Release guarantees

- EIS does not select an LLM provider implicitly.
- Generated content is not treated as evidence without provenance.
- Tool and execution capabilities remain explicit application-owned boundaries.
- Verification and evidence quality are not removed as performance optimizations.
- A 1.0.0 release must pass the complete release gate on the exact release commit before tagging or publishing.

### Known limitations

- The default SDK state is in-process rather than a distributed persistence service.
- External model, repository, knowledge, database, and execution providers require explicit adapters/configuration.
- Performance benchmarks use deterministic local doubles; production provider latency and cost must be measured from live observability.
