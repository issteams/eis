# EIS Tool and Execution System

Phase 8 provides a security boundary between agents and real-world execution.

## Security model

Agents never receive unrestricted shell, filesystem, Python, or network access. A request must pass, in order:

1. registered-tool lookup
2. execution-limit validation
3. declared permission validation
4. execution-policy validation
5. tool-specific validation
6. bounded execution with a timeout
7. bounded output capture
8. audit recording

Every request produces an `AuditEvent`, including denied, failed, timed-out, and unknown-tool requests.

## Execution policies

- `READ_ONLY`: inspection only.
- `SAFE_WRITE`: narrowly scoped writes, such as writes beneath a configured filesystem root.
- `CONTROLLED_WRITE`: operations that can change project state and require explicit permission.
- `HIGH_RISK`: dangerous capabilities disabled by the default security policy.
- `PROHIBITED`: never executable by the local backend.

The policy is deliberately separate from tool implementation so deployments can add stricter authorization without changing agent APIs.

## Built-in tools

The initial tool set includes filesystem, shell, Git, repository inspection, test execution, Python execution discovery, and HTTP access.

- Filesystem paths are resolved under a configured root and traversal is rejected.
- Shell uses argv-based subprocess execution and never invokes a shell interpreter. Commands must be explicitly allowlisted.
- Git is restricted to read-only inspection commands.
- Test execution is restricted to `pytest` and remains controlled.
- Local Python execution is explicitly prohibited.
- HTTP requires HTTPS and an explicit host allowlist and only permits GET/HEAD by default.

## Sandbox boundary

`ExecutionBackend` is the abstraction boundary for the environment. The current subprocess implementation is local, but a container, VM, remote worker, or OS sandbox can replace it without changing the agent-facing models or execution policy layer.

## Agent integration

`AgentToolAdapter` bridges the Phase 7 `invoke(step)` contract to `SecureExecutor`. It requires explicit permission grants supplied by the agent integration layer; it does not manufacture permissions from the tool definition.
