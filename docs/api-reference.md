# EIS SDK API Reference

## `eis`

- `EIS`
- `__version__`

## `eis.sdk`

### Core

- `EIS`
- `EISClient` (legacy configuration facade retained for compatibility)

### Models

- `Product`
- `KnowledgeItem`
- `Task`
- `TaskStatus`
- `TaskResult`
- `AgentResult`
- `EvaluationResult`
- `EngineeringResult`
- `AuditEntry`

### Extension contracts

- `Agent`
- `Evaluator`
- `Engineer`

## Main operations

| API | Purpose |
| --- | --- |
| `EIS()` | Initialize an SDK instance |
| `register_product()` | Register a product |
| `add_knowledge()` | Add traceable knowledge |
| `search_knowledge()` | Retrieve SDK knowledge |
| `remember()` / `memories()` | Manage simple SDK memory |
| `create_task()` | Create a task |
| `task_result()` | Inspect task state |
| `register_agent()` | Register an application-owned agent |
| `run_agent()` | Run an agent |
| `evaluate_idea()` | Evaluate an idea through an explicit evaluator |
| `execute_engineering()` | Execute engineering through an explicit adapter |
| `audit_history()` | Retrieve sanitized audit history |

See `docs/sdk.md` for stability and integration rules.
