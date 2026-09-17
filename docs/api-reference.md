# EIS SDK API Reference

The supported application-facing import surfaces are `eis` and `eis.sdk`. Runtime modules outside the SDK are implementation details unless explicitly documented.

## Package

### `eis`

- `EIS`
- `__version__`

### `eis.sdk`

Core: `EIS`, `EISClient`.

Models: `Product`, `KnowledgeItem`, `MemoryItem`, `Task`, `TaskStatus`, `TaskResult`, `AgentResult`, `EvaluationResult`, `EngineeringResult`, `ExecutionResult`, `WorkflowResult`, `AuditEntry`.

Contracts: `Agent`, `Evaluator`, `Engineer`, `Executor`, `Tool`, `Orchestrator`.

## `EIS` operations

| Method | Behavior |
| --- | --- |
| `EIS()` | Creates an in-process SDK instance with empty product, knowledge, memory, task, agent, tool, and audit collections. |
| `register_product(product, purpose=None)` | Registers/replaces a product by name. A string product requires `purpose`. |
| `products()` | Returns registered products as a tuple. |
| `add_knowledge(item, source=None, title=None)` | Stores a `KnowledgeItem`. Raw string content requires a source. |
| `search_knowledge(query)` | Performs simple case-insensitive substring lookup over title/content; an empty query returns all knowledge. |
| `remember(content, metadata=None)` | Stores a non-empty `MemoryItem`. |
| `memories()` | Returns stored memories as a tuple. |
| `create_task(objective, input=None)` | Creates a task and an initial `QUEUED` task result. |
| `task_result(task_id)` | Returns the stored task result or `None`. |
| `register_agent(name, handler)` | Registers an application-owned agent handler. |
| `run_agent(name, task)` | Runs a registered sync/async handler and normalizes its result to `AgentResult`. |
| `register_tool(name, handler)` | Registers an application-owned tool handler. |
| `execute(name, *args, **kwargs)` | Runs a registered sync/async tool and normalizes its result to `ExecutionResult`. |
| `evaluate_idea(subject, evaluator)` | Runs an explicit evaluator and requires an `EvaluationResult`. |
| `execute_engineering(task, engineer)` | Runs an explicit engineering adapter and returns `EngineeringResult`; adapter exceptions are represented as failed engineering results. |
| `orchestrate(workflow, task, runner)` | Runs an explicit workflow adapter and returns `WorkflowResult`. |
| `audit_history(limit=None)` | Returns SDK audit entries, optionally limited to the newest entries. |

## Executable SDK example

```python
import asyncio

from eis import EIS
from eis.sdk import AgentResult


async def main() -> None:
    eis = EIS()
    eis.register_product("CraftIQ", "AI marketing platform")
    eis.add_knowledge("CraftIQ is an AI marketing platform.", source="organization")

    task = eis.create_task("Inspect the product architecture")

    async def architect(task):
        return AgentResult(
            agent="architect",
            task=task,
            output={"status": "inspected"},
            completed=True,
        )

    eis.register_agent("architect", architect)
    result = await eis.run_agent("architect", task)
    assert result.completed is True
    assert eis.task_result(task.id) is not None


asyncio.run(main())
```

This example uses only the public SDK and no external provider. For model/provider integrations, supply the appropriate application-owned adapter rather than assuming EIS selects one automatically.

See [`docs/sdk.md`](sdk.md) for API stability rules.
