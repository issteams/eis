# Integrations

EIS is designed around explicit adapters rather than hard-coded external providers.

## Model providers

The model layer exposes provider-independent contracts for generation, structured generation, embeddings, tool calls, streaming, metadata, usage, and cost. Provider adapters implement those contracts.

The SDK does not automatically select a provider. Applications supply the adapter they need.

## Repository systems

Repository access is represented as an explicit integration/capability boundary. EIS architecture supports repository inspection and engineering workflows, but a deployment must provide the concrete repository adapter it intends to use.

## Knowledge backends

The knowledge architecture supports a backend boundary. The base SDK itself uses in-process knowledge storage and simple lookup; a production deployment can provide an explicit backend adapter.

## External execution

Tools and executors are explicit capabilities. EIS does not expose unrestricted shell execution through the public SDK.

## HTTP/API integration

The current repository documents and exposes a Python SDK; it does not ship a FastAPI HTTP server in this documentation set. An HTTP service can wrap the SDK later without changing the domain contracts.

## Integration rule

When an integration is unavailable, EIS should report that fact or fail at the boundary. It must not simulate a successful external operation.

See `docs/architecture/integration.md` and `docs/architecture/model-abstraction.md` for the detailed contracts.
