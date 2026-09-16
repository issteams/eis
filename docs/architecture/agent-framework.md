# EIS Agent Framework

The agent framework provides a bounded runtime for general-purpose EIS agents. It does not grant agents direct machine access and does not implement autonomous coding behavior.

## Agent model

An `Agent` carries identity, role, capabilities, permissions, objectives, context, registered tools, policies, execution limits, state-related runtime information, memory, and observability hooks.

Tasks become explicit `AgentTask` objects. Planning produces an `AgentPlan` containing `AgentStep` values. Execution returns an `AgentResult` with the terminal state, output, errors, escalation status, and observations.

## Controlled execution

Tools are registered with the runtime. An agent cannot invoke an arbitrary machine operation by name. Every planned step must:

1. Resolve to a registered tool.
2. Match an explicit `AgentPermission` for the requested action and resource, or an explicit wildcard resource permission.
3. Pass every configured policy check.
4. Execute through the tool interface.
5. Produce an observation for the observability hook.

A missing permission, missing tool, or denied policy is a controlled failure and enters `ESCALATE`. An optional escalation handler can take over; otherwise the runtime returns an escalated `AgentResult`.

## Lifecycle

```text
RECEIVE -> UNDERSTAND -> PLAN -> EXECUTE -> OBSERVE -> VERIFY -> COMPLETE
                                      |
                                      +--------------------------> ESCALATE
```

The runtime is deliberately deterministic at this layer. Planning, tools, policies, memory, and observability are interfaces or injected components rather than privileged global services.

## Future extensions

Future phases can add persistent state, richer execution budgets, model-backed planning, tool schemas, policy composition, human approval gates, durable memory, tracing, and specialized agent implementations without weakening the permission boundary.
