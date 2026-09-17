# Specialized EIS Agents

Phase 11 adds specialized roles on top of the common EIS Agent Framework. Specialties are contracts, not separate runtimes: every agent uses the shared knowledge, memory, context, integrity, tools, execution, and verification boundaries.

## Specialties

| Agent | Responsibility | Write authority |
| --- | --- | --- |
| Research | Evidence gathering and synthesis | None |
| Product | Requirements and product trade-offs | None |
| Architecture | Design and integration review | None |
| Engineering | Controlled implementation | Controlled |
| Testing | Behavioral and regression validation | None |
| Security | Threat and security review | None |
| Documentation | Accurate technical documentation | Controlled |
| Analysis | Evidence synthesis and uncertainty analysis | None |

Each `AgentSpec` explicitly declares capabilities, permissions, inputs, outputs, and limitations. The shared runtime remains the enforcement point for agent permissions and policies.

## Coordination

`AgentOrchestrator` assigns bounded work through an `AgentFactory`. It does not create a second execution stack. Results are retained by agent kind and agents may challenge another agent's output through the shared challenge protocol.

A typical product change can therefore flow through product proposal, architecture review, security challenge, controlled engineering, testing, and independent verification. The orchestrator itself does not declare work correct; verification remains authoritative.

## Safety

The orchestrator enforces a maximum number of assignments. Specialized agents cannot acquire permissions merely by declaring a capability. Actual machine access remains behind the Phase 8 execution and policy boundary, while Phase 10 verification remains independent of builder conclusions.
