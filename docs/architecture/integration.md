# Phase 18 — Echowavs Integration

Phase 18 connects EIS to real Echowavs systems without placing external-service dependencies in EIS core.

## Architecture

```text
EIS core
  |
  +-- integration protocols
        |
        +-- GitHub adapter
        +-- local repository adapter
        +-- future documentation / CI / issue / internal API adapters
```

Adapters implement stable protocols and translate provider-specific data into EIS integration models.

## Available integrations

### GitHub

`GitHubConnector` supports:

- repository discovery for an authenticated GitHub account
- repository tree inspection
- recent commit/change retrieval
- Markdown/RST/text documentation ingestion
- GitHub Actions run retrieval
- issue creation

The adapter uses the GitHub REST API through `httpx`. A token is optional for public resources but is required for private/account-scoped discovery. EIS does not store credentials in source code.

### Local repositories

`LocalRepositoryConnector` supports controlled inspection and documentation ingestion from a configured local path. It skips common generated/dependency directories such as `.git`, `.venv`, `node_modules`, and `__pycache__`.

## Security boundary

Every adapter operation passes through `IntegrationSecurity` and `SecurityGateway`.

- reads require EIS authorization and are audited after the external operation
- writes require authorization, governance checks, and high-risk approval
- successful and failed external operations are audited
- secret-bearing audit fields continue to use the existing redaction layer
- external adapters never bypass EIS authorization by calling provider APIs directly

Phase 18 adds a two-stage security boundary: `prepare()` authorizes before the external side effect and `complete()` records the actual outcome afterward.

## Engineering workflow

`EchowavsIntegration` provides the integration-level workflow primitives:

1. discover repositories
2. inspect a repository
3. ingest documentation
4. assemble project context from structure, documentation, changes, and CI
5. create a typed engineering request
6. execute approved external work through an adapter
7. retrieve CI results for verification

The engineering agent remains responsible for planning, implementation, testing, correction, and reporting. Integration adapters only provide controlled access to external systems.

## Credentials and unavailable infrastructure

EIS must never invent an integration. An adapter is only active when its endpoint, credentials, and infrastructure are actually configured. Missing integrations fail explicitly rather than silently simulating external state.

For GitHub, configure the token outside source control, for example through the application's secret provider/environment. The integration layer does not define or commit real credentials.

## Current scope

Implemented real provider integration:

- GitHub repositories, contents, commits, Actions, and issues
- local development repositories

Defined extension points, but not claimed as implemented real providers:

- arbitrary CI/CD platforms
- external issue trackers
- Echowavs internal APIs
- product systems
- remote development environments

Those systems require concrete endpoints, authentication, contracts, and infrastructure before an adapter should be enabled.
