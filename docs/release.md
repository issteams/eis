# Release Process

EIS uses the package version in `pyproject.toml` as the release version. The public SDK currently reports the same version through `eis.__version__`.

## Release checklist

1. Review changes since the previous release.
2. Confirm public API and architecture documentation match implementation.
3. Run lint, formatting, strict type checking, and the full test suite.
4. Run the deterministic performance benchmark.
5. Review security/governance implications.
6. Update the version in `pyproject.toml` and `src/eis/__init__.py` together when a release version changes.
7. Commit the release change.
8. Create the corresponding Git tag/release through the repository release workflow used by the maintainers.
9. Record breaking changes and migration instructions when applicable.

## Versioning

The SDK documentation follows semantic-versioning expectations: breaking public API changes require a major-version treatment where the project's release policy permits it, compatible additions are minor changes, and compatible fixes are patch changes.

## Release quality bar

A release must not claim an external integration, model provider, deployment mode, or operational guarantee that was not actually verified. Test results should be reported from the exact release commit.

## Post-release

Verify the published package/version, deployment health, workflow recovery behavior, and relevant observability after rollout. If a release introduces a regression, follow the repository's incident/reversion process and document the corrective release.
