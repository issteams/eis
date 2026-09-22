# Organizational Intelligence

The organizational intelligence layer represents organization-specific facts independently from
agent implementations. EIS agents can consume organizational knowledge without embedding a
particular organization's assumptions in agent logic.

The model supports:

- organizations
- divisions
- teams
- products
- projects
- repositories
- responsibilities
- relationships
- standards
- policies
- workflows
- strategic objectives

## Product profiles

`ProductProfile` is the stable product contract. It contains identity, purpose, architecture,
repositories, technology stack, engineering standards, dependencies, current status, roadmap,
constraints, and extensible metadata.

A new product is data, not a new code path. `InMemoryOrganizationStore` accepts additional
product profiles without modifying the core architecture.

## Unknown information

Missing organizational facts are represented explicitly by the `UNKNOWN` sentinel. EIS must not
infer an organizational fact merely because a field is empty or because an agent expects one to exist.

## Retrieval and isolation

`OrganizationStore` provides stable access to organization data and product retrieval. Retrieval
can be constrained by product ID or entity kind so information from one product does not silently
become context for another product.

Relationships are explicit records rather than implicit agent knowledge.

## Bundled example data

`src/eis/organization/data.py` contains a deliberately generic example configuration. It is
safe for public distribution and is intended to be replaced or extended by an application's own
organization-specific configuration.

A deployment can provide its own persistent database, document-backed configuration, or remote
organizational knowledge service without changing specialized agents.
