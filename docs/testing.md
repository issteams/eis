# Testing Guide

EIS uses pytest for tests, pytest-cov for coverage, Ruff for lint/formatting, and mypy in strict mode.

## Full validation

```bash
ruff check .
ruff format --check .
mypy src
pytest --cov=eis --cov-report=term-missing
```

The repository configuration sets a 90% minimum coverage threshold.

## Test organization

Tests live under `tests/` and mirror major runtime boundaries. Performance tests cover caching, context optimization, routing, scheduling, retries, profiling, and observability integration.

## Benchmarking

Run the deterministic local performance benchmark with:

```bash
python -m benchmarks.performance
```

The benchmark intentionally uses local deterministic doubles for model/tool behavior so it can run without provider credentials or network access. Production provider latency and cost must be measured through EIS observability rather than inferred from the local benchmark.

## Writing tests

New behavior should include tests for:

- successful behavior;
- invalid input and boundary conditions;
- failure propagation;
- security or authorization boundaries when applicable;
- preservation of provenance/verification where applicable;
- deterministic infrastructure behavior.

Do not weaken assertions merely to make CI pass. If an expected behavior changes, update the implementation and documentation together.
