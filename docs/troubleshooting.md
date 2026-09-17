# Troubleshooting

## `unknown agent: ...`

Register the application-owned agent before calling `run_agent()`:

```python
eis.register_agent("architect", handler)
await eis.run_agent("architect", task)
```

## `unknown tool: ...`

Register the tool before execution:

```python
eis.register_tool("repository.inspect", handler)
await eis.execute("repository.inspect", path="src/eis")
```

## `purpose is required when registering by name`

`register_product("Name")` requires a purpose. Use either a complete `Product` or provide the purpose argument.

## `source is required when adding knowledge by content`

Knowledge added as raw content must include a source. Alternatively pass a `KnowledgeItem`.

## Empty objective/subject/content errors

Task objectives, evaluation subjects, memory content, agent/tool names, and workflow names have explicit non-empty validation. Correct the input instead of bypassing validation.

## Provider is configured but nothing calls it

EIS configuration declarations do not automatically install or select providers. Supply the concrete model/integration adapter required by the application.

## Performance looks different in production

The local benchmark uses deterministic local doubles. Provider latency, database latency, network latency, and real token/cost usage must be measured in the deployment through observability.

## Cache behavior is process-local

The Phase 20 async response cache is bounded and in-process. Do not treat it as a distributed cache across workers or hosts.

## Coverage fails below 90%

Add tests for the new behavior or intentionally refactor unreachable/dead code. Do not reduce the configured threshold simply to pass CI.
