# EIS Integrity Engine

## Purpose

The Integrity Engine is the enforcement layer for EIS's **Honest Intelligence** principle. It is designed to prefer truthfulness, evidence, transparency, and useful correctness over agreement or confidence for its own sake.

The engine is deterministic at this phase and does not require an LLM, vector database, or external provider.

## Claim taxonomy

EIS distinguishes:

- `FACT` — a claim presented as factual but not necessarily independently verified.
- `VERIFIED_FACT` — a fact with explicit corroboration requirements.
- `OBSERVATION` — something directly observed or recorded.
- `INFERENCE` — a conclusion derived from evidence.
- `ASSUMPTION` — an input accepted provisionally because evidence is incomplete.
- `OPINION` — a judgment that should not be represented as objective fact.
- `PROPOSAL` — a suggested action or design, not a fact.
- `UNKNOWN` — information for which EIS does not have enough knowledge to assert a conclusion.
- `CONFLICTING_EVIDENCE` — evidence that materially disagrees and has not been resolved.
- `UNCERTAIN` — a claim whose uncertainty is material to its interpretation or use.

The taxonomy is descriptive. A stored label never makes a statement true.

## Evidence and provenance

`EvidenceItem` carries source provenance, evidence kind, confidence, observation time, optional expiry, claim key, polarity, and metadata.

Every assessment retains the evidence used to support or contradict a claim. Provenance points back to the existing knowledge source model rather than creating a second source system.

## Confidence

Confidence is explicit and bounded to `[0, 1]` with a required basis. A confidence value describes the strength of an assessment; it is not a probability that the statement is true unless a future calibrated system establishes that interpretation.

`ConfidenceCalibrator` is a replaceable interface. The initial implementation is deliberately simple and must not be treated as a truth estimator.

## Freshness

Evidence can have an expiry time. Expired evidence is retained for traceability but cannot create fresh certainty. Matching stale evidence adds explicit uncertainty and causes the claim to require more evidence.

## Contradictions

Contradictions are explicit. Evidence with the same claim key but opposite polarity is treated as contradictory evidence. The engine does not silently choose the newest or most convenient source.

A contradiction produces `QUESTIONABLE` rather than an arbitrary winner.

## Unsupported claims

A claim with no attributable supporting evidence is not promoted to a supported conclusion. The engine distinguishes:

- `INSUFFICIENT_EVIDENCE` — there is not enough attributable evidence to establish the claim.
- `UNSUPPORTED` — relevant evidence exists but does not support the claim.

This distinction prevents missing evidence from being mistaken for negative evidence.

## Honest responses

`HonestResponse` exposes:

- the answer
- claims currently supported as known
- unsettled claims represented separately as beliefs/working claims
- supporting and available evidence
- uncertainty
- explicit invalidators
- individual claim assessments

This structure is intended to be consumed by future reasoning and agent layers.

## Idea evaluation

`IdeaEvaluation` is an evidence-based assessment framework, not an approval system. Criteria can represent objective, assumptions, existing functionality, duplication, feasibility, complexity, security, scalability, maintenance, business relevance, dependencies, risks, and unknowns.

The resulting status can be:

- `SUPPORTED`
- `UNSUPPORTED`
- `QUESTIONABLE`
- `INSUFFICIENT_EVIDENCE`
- `TECHNICALLY_RISKY`
- `NEEDS_INVESTIGATION`

The engine retains criterion-level assessments, risks, dependencies, unknowns, and investigation paths so a status never replaces the reasoning behind it.

## Integrity invariants

1. No evidence means no evidence-backed certainty.
2. Storage does not make a claim authoritative.
3. Provenance is retained with evidence.
4. Stale evidence cannot silently become fresh evidence.
5. Conflicting evidence is surfaced rather than silently resolved.
6. Confidence must have an explicit basis.
7. Unknown is a valid result.
8. An opinion is not converted into a fact by repetition.
9. A proposal is not represented as an existing capability.
10. Unsupported claims must remain distinguishable from facts.
11. Future model output must pass through these integrity boundaries before being treated as reliable system knowledge.
12. The engine must explain what evidence would change a conclusion.

## Relationship to Knowledge and Memory

Knowledge remains the canonical organizational knowledge system. Memory remains contextual, lifecycle-aware recollection and is not authoritative by storage alone. The Integrity Engine evaluates evidence and claims across those systems; it does not duplicate either persistence model.

## Future extensions

Future phases may add model-assisted claim extraction, richer semantic contradiction detection, source authority policies, temporal reasoning, statistical calibration, and evaluation datasets. Those capabilities must implement the same interfaces and preserve the invariants above.
