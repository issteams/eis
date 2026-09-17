# EIS — Echowavs Intelligence System

EIS is the central intelligence and controlled autonomous execution platform of Echowavs.

> **Defining principle: Honest Intelligence.**

EIS is designed to understand Echowavs, its products, engineering standards, decisions, repositories, workflows and organizational knowledge; evaluate ideas honestly; support research and planning; build and verify software; and eventually operate as a controlled autonomous system.

## Honest Intelligence

EIS must not optimize for agreement. It must distinguish:

- **Fact / evidence** — information supported by a traceable source.
- **Inference** — a conclusion derived from available evidence.
- **Opinion** — a preference or value judgment.
- **Uncertainty** — what is unknown, weakly supported, or ambiguous.
- **Proposed action** — an action that may be taken, subject to applicable policy and authorization.

When evidence is insufficient, EIS must be able to say so. It must never manufacture certainty or claim that an unimplemented capability works.

## Foundation status

The repository contains the production-oriented architectural foundation of EIS, including organizational intelligence, model abstraction, context retrieval, agent lifecycle contracts, secure tools, autonomous engineering, verification, specialized agents, security/governance, production infrastructure/observability, controlled external integrations, and resumable end-to-end engineering workflows.

The model layer defines stable interfaces for generation, structured generation, embeddings, tool calls, streaming, model metadata, usage and cost tracking. Provider adapters remain behind those interfaces.

## Architecture

```text
src/eis/
├── core/          # shared contracts, value objects, errors
├── config/        # typed environment configuration
├── knowledge/     # canonical organizational knowledge boundary
├── memory/        # session/agent memory boundary
├── reasoning/     # evidence-aware reasoning contracts
├── integrity/     # provenance and honesty invariants
├── models/        # provider-independent model abstraction
├── agents/        # agent capability/lifecycle contracts
├── tools/         # explicit external capability contracts
├── execution/     # controlled side effects
├── evaluation/    # verification and evaluation contracts
├── orchestration/ # workflow coordination
├── workflows/     # durable end-to-end engineering workflows
├── security/      # authorization and policy boundary
├── observability/ # logs, metrics, traces, health and job recovery
├── adapters/      # replaceable infrastructure providers
├── integrations/  # controlled Echowavs system adapters
└── sdk/           # public SDK facade
```

The core is deliberately independent of any particular LLM provider, embedding engine, vector database, repository host or execution technology. Provider adapters implement protocols instead of being imported by domain code.

## Autonomous engineering workflows

Phase 19 provides a durable workflow boundary for high-level engineering requests. A request can move through understanding, knowledge retrieval, product inspection, evaluation, risk identification, planning, architecture review, approval, implementation, testing, debugging, correction, security review, requirement verification, documentation, and final reporting.

Workflows are persisted in SQLite and can safely stop at human approval checkpoints, survive process interruption, resume from the stored phase, and escalate when autonomous continuation is unsafe. External capabilities are injected through operation protocols; EIS does not invent or tightly couple unavailable integrations.

See [`docs/architecture/autonomous-workflows.md`](docs/architecture/autonomous-workflows.md) for the workflow and governance model.

## Production operations

See [`docs/architecture/production.md`](docs/architecture/production.md) for deployment topology, health/readiness behavior, recovery semantics, observability dashboards, safe degradation and scaling guidance.

A non-secret environment configuration template is provided at [`deploy/production.env.example`](deploy/production.env.example). Credentials and provider keys must come from the deployment environment or a secret manager; they are never committed to the repository.

## Development

Requirements: Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
ruff check .
ruff format --check .
mypy src
pytest --cov=eis --cov-report=term-missing
```

CI runs linting, formatting checks, strict type checking and tests on Python 3.11 and 3.12.

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — architecture and domain boundaries.
- [`docs/architecture/production.md`](docs/architecture/production.md) — production infrastructure and observability.
- [`docs/architecture/autonomous-workflows.md`](docs/architecture/autonomous-workflows.md) — Phase 19 workflow lifecycle and governance.
- [`docs/development.md`](docs/development.md) — setup and engineering rules.
- [`docs/decisions/0001-foundation-boundaries.md`](docs/decisions/0001-foundation-boundaries.md) — initial architecture decision record.
