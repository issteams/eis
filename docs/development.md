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
mypy src\pytest
pytest --cov=eis --cov-report=term-missing
```

## Rules

- Put stable contracts in protocols, not provider implementations.
- Keep side effects behind `execution` and `tools` boundaries.
- Never treat generated text as evidence without provenance.
- Represent uncertainty explicitly.
- Do not add a dependency to core unless it is genuinely domain-level.
- Prefer dependency injection over global provider clients.
- Add tests for every new contract and security/integrity invariant.
- Do not merge a placeholder that claims to perform a capability it does not perform.

## Versioning

EIS follows Semantic Versioning once the public SDK is stable. During 0.x, breaking changes are expected and must be recorded in architecture decisions and release notes. The package version is declared in `pyproject.toml` and `src/eis/__init__.py`.
