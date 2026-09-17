# EIS Production Infrastructure and Observability

Phase 14 establishes the operational boundary for deploying EIS as a service and worker system.

## Runtime topology

```text
Client / internal application
          |
      API/service
          |
   SecurityGateway
          |
   +------+----------------+
   |                       |
Task queue              Model/tool adapters
   |                       |
Worker pool            external providers
   |
SQLite/Postgres job state

Observability -> structured logs / metrics / traces -> operational backend
Health probes -> liveness and readiness endpoints
```

The package intentionally keeps provider-specific infrastructure behind interfaces. A production deployment may replace the reference in-process metrics/tracing and SQLite job store with Prometheus/OpenTelemetry and a managed relational/queue backend without changing EIS domain APIs.

## Configuration

`ProductionSettings` reads `EIS_*` environment variables. No secret is stored in source code. Use the deployment platform's secret manager for credentials and provider keys.

Important controls include request/model/tool timeouts, bounded retries, worker concurrency, queue name, task lease duration, maximum task attempts, and persistent job path.

Example environment configuration:

```text
EIS_ENVIRONMENT=production
EIS_LOG_JSON=true
EIS_LOG_LEVEL=INFO
EIS_REQUEST_TIMEOUT_SECONDS=30
EIS_MODEL_TIMEOUT_SECONDS=120
EIS_TOOL_TIMEOUT_SECONDS=120
EIS_MAX_RETRIES=2
EIS_WORKER_CONCURRENCY=4
EIS_MAX_CONCURRENT_TASKS=4
EIS_TASK_LEASE_SECONDS=300
EIS_MAX_TASK_ATTEMPTS=3
EIS_PERSISTENCE_PATH=/var/lib/eis/jobs.sqlite3
```

## Health model

- **Liveness** answers whether the process is alive and able to serve the probe.
- **Readiness** verifies registered dependencies and can be disabled during graceful shutdown.
- Dependency failures produce `not_ready`, not false healthy status.

## Reliability and recovery

Long-running jobs are persisted before execution. Workers claim a lease, increment an attempt count, and complete or fail the job. Expired leases are returned to the queue so interrupted workers do not permanently lose work. Maximum attempts should be enforced by the worker before requeueing indefinitely.

Shutdown must first stop accepting new work, mark readiness false, allow bounded in-flight work to finish, and leave unfinished leased jobs recoverable.

Retries are bounded and should be enabled only for operations known to be safe to retry. High-risk operations remain governed by Phase 13 authorization and approval controls.

## Observability

EIS records structured logs, counters, latency observations, trace spans, task outcomes, tool execution outcomes, model token usage and cost, and verification outcomes. The metrics registry exposes Prometheus-compatible text for lightweight deployments and is deliberately replaceable for a centralized metrics backend.

Operational dashboards should expose:

- request/task throughput and latency
- active workers and queue depth
- task failures and retries
- agent execution duration and failures
- tool execution count, duration and denial/failure rates
- model requests, tokens and estimated cost
- verification pass/failure rates
- readiness and dependency state
- recent traces correlated by trace ID

## Safe degradation

A dependency outage must not silently report success. Readiness should fail when required dependencies are unavailable. Optional observability exporters may degrade independently, but core authorization, verification, task persistence and result correctness must remain authoritative.

## Deployment notes

For a single-node deployment, SQLite can provide the reference durable job state. For multiple workers or horizontally scaled deployments, use a transactional shared database and a durable queue implementation behind the same job boundary. The in-memory metrics, trace list and audit sinks are reference implementations only; production installations should export to durable centralized systems.
