# End-to-End Autonomous Engineering Workflows

Phase 19 adds a durable workflow boundary for high-level engineering requests.

A workflow advances through these phases:

```text
UNDERSTAND
→ RETRIEVE_KNOWLEDGE
→ INSPECT_PRODUCT
→ EVALUATE_IDEA
→ IDENTIFY_RISKS
→ CREATE_PLAN
→ ARCHITECTURE_REVIEW
→ APPROVAL
→ IMPLEMENT
→ TEST
→ DEBUG
→ CORRECT
→ SECURITY_REVIEW
→ REQUIREMENT_VERIFICATION
→ DOCUMENT
→ FINAL_REPORT
```

## Governance

`EngineeringWorkflow` never invokes an operation directly. Every phase execution first passes through `SecurityGateway`, so authorization, approval requirements, governance limits, and audit recording remain outside the workflow implementation.

Implementation is a default human-approval checkpoint. Deployments or other high-risk operations should add their own approval checkpoints rather than weakening the existing one.

An approved checkpoint is persisted with the workflow. A workflow can therefore stop safely, survive process interruption, and resume only after the matching approval is supplied.

## Persistence

`WorkflowStore` uses SQLite with atomic state replacement. Persisted state includes:

- request identity and objective;
- current phase index;
- workflow status;
- phase events and evidence;
- approval checkpoint metadata;
- accumulated workflow data;
- escalation reason.

Terminal workflows are idempotent when loaded again; they are reported rather than executed a second time.

## External systems

The workflow runtime contains no GitHub, CI, product, or deployment implementation. Those capabilities implement `WorkflowOperations` and are injected into the runtime. This keeps EIS core independent from external services and makes unavailable integrations explicit instead of simulated.

The final report separates completed work, evidence, tests, failures, corrections, remaining risks, uncertainty, and human decisions.
