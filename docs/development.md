# Developer Guide

## Setup

Use Python 3.11+ and create a virtual environment.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Quality commands

```bash
ruff check .
ruff format --check .
mypy src
pytest --cov=eis --cov-report=term-missing
```

## Repository boundaries

- Put stable contracts in protocols, not provider implementations.
- Keep side effects behind `execution` and `tools` boundaries.
- Keep provider-specific code behind adapters.
- Never treat generated text as evidence without provenance.
- Represent uncertainty explicitly.
- Do not add a dependency to core unless it is genuinely domain-level.
- Prefer dependency injection over global provider clients.
- Add tests for every new contract and security/integrity invariant.
- Do not merge a placeholder that claims to perform a capability it does not perform.

## Documentation

Update the relevant documentation whenever a public contract, configuration variable, deployment behavior, security boundary, or operational characteristic changes. Document actual behavior at the target commit.

## Performance work

Use the Phase 20 performance primitives where they fit the existing boundary. Do not optimize by removing verification, provenance, authorization, or evidence quality. Run `python -m benchmarks.performance` when changing performance-sensitive infrastructure.

## Versioning

EIS follows Semantic Versioning expectations for the public SDK. During 0.x, breaking changes may still occur but must be recorded in architecture/release documentation. The package version is declared in `pyproject.toml` and `src/eis/__init__.py`.
