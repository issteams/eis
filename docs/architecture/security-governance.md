# EIS Security, Governance and Audit System

Phase 13 establishes a fail-closed security boundary for autonomous EIS actions.

## Security model

The security layer separates authentication, authorization, governance, approval, execution, and audit concerns.

- **Authentication:** `Authenticator` identifies a principal without storing credentials in the security runtime.
- **Authorization:** `RoleAuthorizer` evaluates RBAC roles, agent permissions, and resource restrictions.
- **Agent permissions:** agent-specific permissions are additive only after the principal is authenticated.
- **Tool permissions:** the existing `SecureExecutor` still requires every permission declared by a tool definition.
- **Resource restrictions:** resource patterns can explicitly constrain permitted actions.
- **Secrets:** `SecretProvider` reads secrets on demand; `EnvironmentSecretProvider` does not persist values.
- **Sensitive data:** `RedactingProtector` removes common password/token/API-key/authorization patterns from audit data.
- **Audit:** `AuditRecord` records actor, agent, task, action, tool, target, timestamp, result, risk, authorization, and failure.
- **Governance:** rate, cost, and execution budgets are checked before action and committed after successful authorization.
- **Approval:** high-risk actions require an identified human approval before execution.
- **Fail closed:** unknown principals, roles, permissions, resource restrictions, approvals, and security failures deny execution.

## High-risk operations

The gateway requires human approval for:

- production deployments
- destructive database operations
- repository deletion
- file deletion
- credential changes
- external communications
- financial actions
- any action explicitly classified HIGH or CRITICAL

An approval must identify the approver and include a reason. Pending, rejected, or missing approval cannot authorize execution.

## Existing architecture security review

### Tool execution

The existing Phase 8 boundary already rejected unrestricted shell interpretation, prohibited local Python execution, constrained filesystem paths, restricted Git commands, and limited HTTP to allowlisted HTTPS hosts. Phase 13 additionally:

1. Redacts sensitive request arguments and errors before audit storage.
2. Adds actor, target, and authorization state to tool audit events.
3. Caps structured string/dictionary tool output at the existing output boundary.
4. Keeps prohibited Python execution and high-risk policy defaults intact.
5. Preserves subprocess execution without a shell.

### Agent execution

Phase 7 exposes agent permissions and tools, but autonomous actions must pass through the shared tool/security boundary. Agent-specific permissions cannot bypass tool permission checks.

### Engineering execution

Phase 9 limits iterations, changed files, tool calls, and execution time. Phase 13 adds an independent governance layer for action rate, cost, and execution budgets; these controls should be wired into any production engineering runner before enabling autonomous writes.

### Verification

Phase 10 requires independent verification before reporting success. Security authorization is intentionally separate from verification: passing tests does not grant authorization to perform a restricted action.

### Organizational intelligence

Phase 12 stores organizational facts as data rather than agent logic. Security decisions do not infer permissions from organizational descriptions; explicit roles, permissions, and restrictions are required.

## Production integration rule

Every production autonomous action should enter through `SecurityGateway.execute_approved()` or an equivalent adapter that performs authentication, authorization, governance, approval, execution, and audit as one traceable transaction. Direct access to privileged tools should not be exposed to autonomous agents.

The in-memory audit and approval implementations are deterministic reference implementations. Production deployments should replace them with durable, access-controlled providers without changing the security protocols.
