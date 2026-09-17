# EIS — Echowavs Intelligence System

EIS is the intelligence and controlled autonomous execution foundation of Echowavs.

**Release target: 1.0.0.** The package is not considered released until the release gates in `docs/release-readiness.md` pass on the exact release commit.

> **Defining principle: Honest Intelligence.**

EIS provides explicit boundaries for organizational knowledge, memory, reasoning, agents, tools, controlled execution, verification, security, governance, observability, integrations, durable workflows, and performance optimization.

## Honest Intelligence

EIS distinguishes:

- **Fact / evidence** — supported by a traceable source.
- **Inference** — derived from available evidence.
- **Opinion** — a preference or value judgment.
- **Uncertainty** — unknown, ambiguous, or weakly supported information.
- **Proposed action** — an action subject to authorization and policy.

EIS must not manufacture certainty or claim that an unimplemented integration or capability has succeeded.

Read [`docs/honest-intelligence.md`](docs/honest-intelligence.md) for the behavioral principles.

## Current status

The repository contains a production-oriented Python foundation and public SDK. It includes typed domain contracts, provider-independent model abstractions, knowledge and memory boundaries, agent/tool/execution contracts, verification and integrity components, security/governance, durable engineering workflows, integrations, observability, and Phase 20 performance controls.

The SDK itself keeps simple state in process. External providers and infrastructure are explicit adapters; EIS does not silently choose an LLM, repository host, database, or unrestricted execution environment.

## Architecture

```text
src/eis/
├── core/          # shared contracts, value objects, errors
├── config/        # typed environment configuration
├── knowledge/     # organizational knowledge boundary
├── memory/        # memory boundary
├── reasoning/     # evidence-aware reasoning contracts
├── integrity/     # provenance and honesty invariants
├── models/        # provider-independent model abstraction
├── agents/        # agent capability/lifecycle contracts
├── tools/         # explicit external capability contracts
├── execution/     # controlled side effects
├── evaluation/    # verification/evaluation contracts
├── orchestration/ # workflow coordination
├── workflows/     # durable engineering workflows
├── security/      # authorization and policy boundary
├── observability/ # logs, metrics, health and recovery
├── performance/   # caching, routing, context and scheduling
├── adapters/      # replaceable infrastructure providers
├── integrations/  # controlled system adapters
└── sdk/           # public application facade
```

See [`docs/architecture.md`](docs/architecture.md) and [`docs/vision.md`](docs/vision.md).

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python examples/sdk_quickstart.py
```

The supported public import surfaces are `eis` and `eis.sdk`.

## Phase 20 performance

Phase 20 adds bounded async caching, evidence-aware context optimization, deterministic model routing, bounded scheduling/concurrency, batching, transient-only retries, retrieval optimization, parallel context retrieval, and performance/cost metrics. These controls do not remove verification or provenance.

Run the deterministic local benchmark with:

```bash
python -m benchmarks.performance
```

The benchmark uses local deterministic doubles. Real provider latency, token usage, and cost must be measured from deployment observability.

## Production

Start with [`deploy/production.env.example`](deploy/production.env.example). Production architecture, persistence, recovery, health, observability, and scaling guidance are documented in [`docs/deployment.md`](docs/deployment.md) and [`docs/architecture/production.md`](docs/architecture/production.md).

## Development and validation

```bash
ruff check .
ruff format --check .
mypy src
pytest --cov=eis --cov-report=term-missing
python -m build
```

For the complete release gate, see [`docs/release-readiness.md`](docs/release-readiness.md).

## Documentation map

| Area | Documentation |
| --- | --- |
| Vision | [`docs/vision.md`](docs/vision.md) |
| Core principles | [`docs/principles.md`](docs/principles.md) |
| Honest Intelligence | [`docs/honest-intelligence.md`](docs/honest-intelligence.md) |
| Architecture | [`docs/architecture.md`](docs/architecture.md) |
| Installation | [`docs/installation.md`](docs/installation.md) |
| Configuration | [`docs/configuration.md`](docs/configuration.md) |
| SDK | [`docs/sdk.md`](docs/sdk.md) |
| Knowledge, memory, agents, tools, execution, verification | [`docs/systems.md`](docs/systems.md) |
| Security and governance | [`docs/architecture/security-governance.md`](docs/architecture/security-governance.md) |
| Integrations | [`docs/integrations.md`](docs/integrations.md) |
| Development | [`docs/development.md`](docs/development.md) |
| Release readiness | [`docs/release-readiness.md`](docs/release-readiness.md) |
| Changelog | [`CHANGELOG.md`](CHANGELOG.md) |
