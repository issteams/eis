# Honest Intelligence

Honest Intelligence is the defining behavioral principle of EIS.

EIS distinguishes four kinds of information:

- **Fact / evidence:** supported by a traceable source.
- **Inference:** a conclusion derived from available evidence.
- **Opinion:** a preference or value judgment.
- **Uncertainty:** information that is unknown, ambiguous, weakly supported, or not verified.

A fifth category, **proposed action**, describes an action that may be taken subject to authorization and policy.

## Required behavior

EIS should:

- preserve provenance when moving knowledge through context and reasoning;
- make uncertainty visible instead of filling gaps with fabricated facts;
- keep application-owned evaluators and execution adapters explicit;
- avoid claiming that an unavailable integration has run;
- keep verification separate from optimization;
- record failures at operational boundaries.

## What this means for models

EIS is model-provider independent. A model may generate text or structured output, but the model is not itself the authority for whether a claim is verified. Verification, provenance, policy, and execution boundaries remain application/runtime concerns.

## What this means for performance

Caching, context optimization, routing, batching, retries, and scheduling may reduce infrastructure cost or latency, but they must not silently discard evidence or bypass verification. The Phase 20 performance layer therefore treats evidence preservation and verification as correctness constraints.

## Honest failure

A correct EIS integration can return an explicit failure, unknown state, or incomplete result. Such a result is preferable to presenting an unsupported answer as verified.
