# Configuration

EIS uses typed settings and environment variables. The repository includes `.env.example` for development and `deploy/production.env.example` for production deployment.

## Development configuration

The development template defines:

| Variable | Purpose |
| --- | --- |
| `EIS_ENVIRONMENT` | Runtime environment; default template is `development`. |
| `EIS_RUNTIME_NAME` | Runtime name; default is `eis`. |
| `EIS_LOG_LEVEL` | Logging level; default template is `INFO`. |
| `EIS_MODEL_PROVIDER` | Provider capability declaration; default is `none`. |
| `EIS_EMBEDDING_PROVIDER` | Embedding capability declaration; default is `none`. |
| `EIS_REPOSITORY_PROVIDER` | Repository capability declaration; default is `none`. |
| `EIS_KNOWLEDGE_BACKEND` | Knowledge backend declaration; default is `none`. |
| `EIS_MAX_TOOL_CALLS` | Maximum tool calls declared by the development template. |

These declarations do not install or configure a provider by themselves.

## Production configuration

The production template additionally defines request/model/tool timeouts, retry settings, worker concurrency, task recovery, persistence, and metrics. See `deploy/production.env.example` for the authoritative non-secret example.

Important production variables include:

- `EIS_REQUEST_TIMEOUT_SECONDS`
- `EIS_MODEL_TIMEOUT_SECONDS`
- `EIS_TOOL_TIMEOUT_SECONDS`
- `EIS_MAX_RETRIES`
- `EIS_RETRY_BACKOFF_SECONDS`
- `EIS_WORKER_CONCURRENCY`
- `EIS_MAX_CONCURRENT_TASKS`
- `EIS_TASK_LEASE_SECONDS`
- `EIS_TASK_RECOVERY_INTERVAL_SECONDS`
- `EIS_MAX_TASK_ATTEMPTS`
- `EIS_PERSISTENCE_PATH`
- `EIS_METRICS_ENABLED`

Do not commit credentials, API keys, tokens, or other secrets. Supply them through the deployment environment or an approved secret-management system.

## Configuration principle

A configured capability is not the same thing as an implemented external integration. Provider adapters must still be explicitly supplied and tested at the relevant application boundary.
