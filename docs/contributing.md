# Contribution Guide

## Scope

Contributions should preserve EIS boundaries: explicit capabilities, provider independence, traceable evidence, controlled side effects, verification, and auditable behavior.

## Before changing code

1. Read the relevant architecture document.
2. Identify the public boundary being changed.
3. Check whether an existing protocol or value object already represents the behavior.
4. Decide whether the change is implementation, public API, integration, or architecture.

## Implementation rules

- Keep domain code independent from concrete providers where the architecture requires it.
- Prefer typed contracts and explicit dependencies.
- Do not introduce unrestricted execution paths.
- Preserve provenance and verification semantics.
- Add tests for new behavior and failure modes.
- Update documentation whenever public behavior changes.

## Validation

Run:

```bash
ruff check .
ruff format --check .
mypy src
pytest --cov=eis --cov-report=term-missing
```

## Documentation changes

Documentation must describe the code that exists at the target commit. If a design is planned but not implemented, label it as future work rather than documenting it as an available feature.

## Pull requests

A pull request should explain the behavior changed, affected boundaries, tests run, and any operational/security implications. Breaking public SDK changes require particular care and should follow the release policy.
