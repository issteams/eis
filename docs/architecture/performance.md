# Phase 20 — Performance, Scalability and Cost Optimization

Phase 20 adds performance controls without weakening EIS verification, provenance, or honesty requirements.

## What is measured

| Area | Measurement |
|---|---|
| Retrieval | retrieval latency, returned evidence count |
| Models | request latency, input/output/total tokens, provider/model, estimated cost |
| Agents | end-to-end task latency and retries |
| Tools | execution count, latency and failures |
| Memory | process RSS and benchmark peak allocation |
| Database | operation latency and row counts |
| Concurrency | bounded workers/batches and scheduler queue depth |
| Cost | token-derived model cost and cost per task |

`PerformanceRecorder` maps retrieval, database, memory, agent and model measurements into the existing observability registry. `PerformanceProfiler` provides local p50/mean/max timing summaries.

## Optimizations

### Caching

`AsyncResponseCache` is bounded by entry count and TTL and provides per-key single-flight behavior. Callers must explicitly mark an operation cacheable. Verification-sensitive, authorization-sensitive, and freshness-sensitive operations should remain uncached unless their caller can prove cache safety.

### Context optimization

`optimize_context` deduplicates evidence and selects the highest-ranked evidence within a deterministic budget. It never rewrites evidence or removes provenance. Context reduction is therefore a transport/token optimization, not a reduction in verification requirements.

### Retrieval

Lexical retrieval now uses top-k heap selection instead of sorting the entire scored set. This keeps the scoring function unchanged while reducing ranking overhead from approximately `O(n log n)` to `O(n log k)`.

Independent context retrievers execute concurrently and are ranked only after all results arrive, preserving deterministic evidence ranking.

### Model routing

`ModelRouter` routes by task metadata when no explicit model is supplied. An explicit model always wins. Verification and security-review tasks can be mapped to dedicated routes; routing never changes evidence requirements or verification policy.

### Task prioritization and concurrency

`TaskScheduler` uses bounded priority queues and a fixed worker count. Queue bounds create backpressure instead of allowing unbounded memory growth. `batch_gather` similarly limits bursts for independent operations.

### Retry optimization

`retry_optimized` retries only failures explicitly classified as transient, uses capped exponential backoff, and adds small jitter. Validation, authorization and correctness failures should not be retried.

## Cost model

Model usage is recorded from provider-reported token counts. Cost is an estimate based on the configured model/provider pricing data; it is not presented as an invoice. `ModelRouter.estimate_cost()` provides a deterministic per-request estimate when route pricing is configured.

The local benchmark uses example pricing only and must not be interpreted as current provider pricing.

## Scalability limits

The default in-memory components are intentionally bounded but process-local:

- `AsyncResponseCache`: bounded by configured entries; not shared across processes.
- `TaskScheduler`: bounded queue and fixed workers; horizontal scaling requires an external durable queue.
- `MetricsRegistry`/`Tracer`: in-process memory; production deployments should export/aggregate externally.
- `InMemoryRetriever`: retrieval cost grows with the number of stored items; a production vector/search backend is required for large corpora.
- SQLite workflow persistence is appropriate for single-node workloads and development; high-concurrency deployments should use a server database with connection pooling.
- Model providers remain the dominant latency and cost variable for real workloads.

These are operating boundaries, not claims of maximum throughput. Capacity must be established with workload-specific load tests against the deployed provider, database, network and hardware.

## Benchmarking

Run the deterministic local suite:

```bash
python -m benchmarks.phase20
```

It writes `benchmark-results/phase20.json` and measures retrieval, model-call overhead, agent execution, tool execution, memory, SQLite, bounded concurrency, scheduling, context optimization and an example token-cost calculation.

The model benchmark intentionally uses a local deterministic double so CI does not depend on a network provider. Production profiling should combine these benchmarks with the live EIS observability metrics for real provider latency, token consumption and cost.

## Correctness guardrail

Performance changes must not:

- remove verification stages;
- lower evidence quality requirements;
- discard provenance;
- turn uncertain results into certain results;
- bypass authorization or policy gates;
- retry non-transient correctness or validation failures.

The target is less redundant work and better resource utilization, not weaker intelligence or evidence.
