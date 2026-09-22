# EIS SDK

The EIS SDK is the stable application-facing interface for the Echowavs Intelligent System.
Applications should import public SDK types from `eis` or `eis.sdk`. Internal runtime modules are
implementation details and are not part of the supported public API.

## Quick start

```python
from eis import EIS, KnowledgeItem, Product

eis = EIS()
eis.register_product(Product(name="Example Product", purpose="Example application"))
eis.add_knowledge(
    KnowledgeItem(
        title="Example Product",
        content="Example Product is an application using EIS.",
        source="organization",
    )
)
```

## Tasks

```python
task = eis.create_task(
    "Design the application architecture",
    input={"product": "Example Product"},
)
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
result = await eis.evaluate_idea("Add autonomous workflow optimization", evaluator)
```

## Engineering

Engineering execution is explicit and application-owned:

```python
result = await eis.execute_engineering(task, engineer)
```

## Tools and execution

Tools must be registered explicitly:

```python
result = await eis.execute("repository.inspect", path="src/eis")
```

The SDK does not expose unrestricted shell execution or bypass the EIS security boundary.

## Orchestration

```python
result = await eis.orchestrate("product-to-engineering", task, orchestrator)
```

## Audit history

```python
audit = eis.audit_history(limit=50)
```

Audit entries expose the SDK-level action history without exposing internal runtime objects.

## Public API stability

The following rules define the supported SDK contract:

1. `eis` and `eis.sdk` are the supported import surfaces.
2. Public classes and protocols are typed and documented.
3. Internal runtime modules are not re-exported as stable SDK APIs.
4. Public API changes follow semantic-versioning expectations.
5. Breaking changes require a deprecation window where practical.
6. SDK behavior must remain provider-independent.
7. New public APIs require tests and documentation.
