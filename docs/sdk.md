# EIS Python SDK

Phase 15 establishes the supported application-facing Python API for EIS.

## Supported imports

```python
from eis import EIS
from eis.sdk import (
    AgentResult,
    AuditEntry,
    EngineeringResult,
    EvaluationResult,
    KnowledgeItem,
    Product,
    Task,
    TaskResult,
    TaskStatus,
)
```

The supported surface is `eis` and `eis.sdk`. Internal packages such as
`eis.agents`, `eis.tools`, `eis.security`, and `eis.observability` are not
SDK stability guarantees.

## Quick start

```python
from eis import EIS

eis = EIS()
product = eis.register_product("CraftIQ", "AI marketing platform")
eis.add_knowledge(
    "CraftIQ is an Echowavs product.",
    source="product-profile",
)
task = eis.create_task("Explain the product architecture")
```

## Agents

Applications provide an explicit agent adapter. EIS does not silently choose a
model or provider.

```python
async def run(task):
    return {"objective": task.objective}

eis.register_agent("architect", run)
result = await eis.run_agent("architect", task)
```

## Evaluation

Evaluation is explicit and typed:

```python
from eis.sdk import EvaluationResult

result = await eis.evaluate_idea(
    "Add a desktop EIS application",
    lambda subject: EvaluationResult(
        subject=subject,
        conclusion="needs-review",
        rationale="Requires a deployment and persistence review.",
        uncertainty="Implementation cost is not yet estimated.",
    ),
)
```

EIS stores the evaluation result in its stable form; it does not manufacture
confidence or conclusions when an evaluator has not been supplied.

## Engineering

Engineering execution is also adapter-driven:

```python
engineering_result = await eis.execute_engineering(task, engineer)
```

An existing `EngineeringAgent` can be wrapped by a small application adapter
that maps its runtime result to `EngineeringResult`. The SDK does not expose
that runtime's internal plan, tool registry, or security implementation.

## Audit history

```python
audit = eis.audit_history(limit=50)
for entry in audit:
    print(entry.action, entry.result, entry.timestamp)
```

Audit entries returned through the SDK are sanitized public records rather than
internal security objects.

## API stability rules

1. Only `eis` and `eis.sdk` are supported import surfaces.
2. Public classes and methods use explicit type annotations.
3. Public models are immutable (`dataclass(frozen=True)`) where practical.
4. Internal runtime classes, provider adapters, storage implementations,
   registries, and execution machinery are not re-exported from the SDK.
5. Breaking changes to supported names, signatures, semantics, or serialized
   public models require a major SDK version according to semantic versioning.
6. Additive, backward-compatible public functionality may be introduced in a
   minor release.
7. Bug fixes and documentation changes use patch releases.
8. Deprecated APIs remain documented for at least one minor release before
   removal unless a security issue requires faster removal.
9. Public APIs must not depend on provider-specific types.
10. Every public API addition requires SDK tests and documentation.

## Design boundary

The SDK is a facade. It is intentionally thinner than the EIS runtime:

`application -> eis.sdk -> stable contracts -> adapters/runtime -> providers`

This prevents consumers from coupling their code to internal architecture and
allows EIS to evolve its agents, models, tools, orchestration, security, and
observability implementations independently.
