# EIS Runtime Systems

This page is the production map of the implemented runtime boundaries. Detailed architecture documents remain authoritative for individual subsystems.

## Knowledge system

The knowledge boundary stores traceable `KnowledgeItem` values in the SDK and provides simple case-insensitive lookup through `search_knowledge()`. The deeper knowledge architecture also defines organizational knowledge, retrieval, provenance, and integration boundaries. A knowledge item should retain a source rather than being presented as unexplained fact.

See `docs/architecture/knowledge-system.md` and `docs/architecture/context-retrieval.md`.

## Memory system

The SDK exposes `remember()` and `memories()` for simple in-process memory. Memory is distinct from canonical organizational knowledge: memory represents retained runtime information, while knowledge is the traceable knowledge boundary.

See `docs/architecture/memory-system.md`.

## Agent system

Applications register an agent handler with `register_agent(name, handler)`. `run_agent()` invokes that application-owned handler and normalizes its output to `AgentResult`. EIS does not silently choose an LLM or provider for an agent.

See `docs/architecture/agent-framework.md`, `engineering-agent.md`, and `specialized-agents.md`.

## Tool system

Applications register tool handlers explicitly with `register_tool()`. `execute()` invokes a named registered tool and normalizes ordinary return values to `ExecutionResult`. Unknown tools raise `KeyError`.

See `docs/architecture/tool-execution.md`.

## Execution system

Execution is the controlled boundary around side effects. The SDK exposes application-owned executor and engineering contracts rather than unrestricted shell access. Durable engineering workflows add persisted workflow state, approval checkpoints, recovery, and escalation.

See `docs/architecture/core-runtime.md`, `docs/architecture/engineering-agent.md`, and `docs/architecture/autonomous-workflows.md`.

## Verification

Evaluation is explicit: `evaluate_idea()` requires an evaluator that returns `EvaluationResult`. Integrity/provenance and verification are separate concerns from generation and execution. Verification is not removed by performance optimizations.

See `docs/architecture/verification.md` and `docs/architecture/integrity-engine.md`.

## Security and governance

Security and governance define authorization, policy, capability boundaries, auditability, safe execution, and escalation. External actions should cross an explicit capability boundary.

See `docs/architecture/security-governance.md` and `docs/security/phase-17-assessment.md`.
