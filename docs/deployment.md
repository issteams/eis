# Deployment Guide

EIS can be embedded as a Python component or run as part of a larger application/runtime. The repository currently provides deployment configuration examples and durable workflow/persistence infrastructure; it does not prescribe a single container image or cloud platform.

## Production configuration

Start from `deploy/production.env.example`. Configure environment, timeouts, retry policy, worker concurrency, task recovery, persistence path, and metrics according to the deployment.

## Persistence

Durable workflow state uses the configured persistence boundary. The production example uses `/var/lib/eis/jobs.sqlite3`. The directory must be writable by the service account and backed up according to the operational requirements of the deployment.

## Concurrency

Phase 20 provides bounded scheduling and concurrency controls. `EIS_WORKER_CONCURRENCY` and `EIS_MAX_CONCURRENT_TASKS` in the production template provide operational limits; tune them using observed workload and provider capacity rather than assuming unlimited parallelism.

## Health and recovery

Production architecture includes health/readiness behavior, task leases, recovery intervals, attempt limits, observability, and safe degradation. See `docs/architecture/production.md` and `docs/architecture/autonomous-workflows.md`.

## Secrets

Never commit provider keys, repository tokens, credentials, or signing material. Inject secrets through the deployment environment or a secret manager.

## Scaling boundary

The Phase 20 response cache is process-local. Multi-process or multi-host deployments should not assume cache sharing. Durable task state and an external/shared coordination layer should be used when the deployment topology requires cross-process coordination.

## Deployment verification

Before promoting a build:

```bash
ruff check .
ruff format --check .
mypy src
pytest --cov=eis --cov-report=term-missing
python -m benchmarks.performance
```

Also verify the actual external adapters used by the deployment, because local deterministic tests do not prove availability of third-party services.
