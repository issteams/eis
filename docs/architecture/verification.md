# Verification and Self-Correction

Phase 10 adds an independent verification boundary after autonomous engineering work.

## Principle

The builder's conclusion is evidence, not proof. The verification engine asks independent verifiers to evaluate the produced work against seven explicit stages:

1. Requirement verification — the implementation satisfies the requested behavior.
2. Code verification — the changed code is syntactically and structurally valid.
3. Test verification — targeted and relevant tests pass.
4. Regression verification — previously working functionality remains intact.
5. Architecture verification — the change respects existing boundaries and reuse decisions.
6. Security verification — the change does not introduce an unacceptable security condition.
7. Quality verification — maintainability and engineering-quality checks pass.

A run can only become `verified` when every required stage passes. Removing an exception, producing a successful tool response, or making one test pass is never sufficient by itself.

## Self-correction loop

When a stage fails, the engine follows:

`IMPLEMENT → TEST → ANALYZE FAILURE → IDENTIFY ROOT CAUSE → PATCH → RETEST → VERIFY`

The correction is represented by `CorrectionRecord`, which preserves:

- original failure
- failure classification
- suspected cause
- change made
- validation result
- remaining uncertainty
- root-cause evidence

`RootCauseAnalysis` is deliberately separate from the builder so the correction decision is not simply the builder's own conclusion repeated.

## Failure classification

Failures are classified as:

- syntax
- type
- test
- runtime
- dependency
- architecture
- security
- requirement
- environment
- unknown

The default analyzer is conservative. If the available evidence does not support a useful classification, it returns `unknown` with zero confidence rather than inventing a cause.

## Correction limits

`VerificationLimits.max_correction_attempts` is a hard bound. When the bound is reached, verification returns an escalated report and does not claim success.

## Regression protection

When a `RegressionGuard` is supplied, the engine first establishes a baseline. After every verification cycle, regression checks are executed against that baseline. A correction that fixes one failure but breaks previously working behavior therefore cannot silently produce a verified result.

## Extension boundary

The engine is provider- and tool-independent. `StageVerifier`, `RootCauseAnalyzer`, `CorrectionRunner`, and `RegressionGuard` are protocols. Concrete implementations can connect the engine to EIS's secure Phase 8 tools and Phase 9 engineering agent without coupling verification to a particular repository, test runner, model provider, or shell implementation.
