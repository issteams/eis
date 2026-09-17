# Organizational Intelligence

Phase 12 adds a data-driven organizational intelligence layer to EIS.

## Purpose

The layer represents organizational facts independently from agent implementations. EIS agents can consume organizational knowledge without embedding Echowavs-specific assumptions in agent logic.

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

`ProductProfile` is the stable product contract. It contains identity, purpose, architecture, repositories, technology stack, engineering standards, dependencies, current status, roadmap, constraints, and extensible metadata.

A new product is data, not a new code path. `InMemoryOrganizationStore` accepts additional product profiles without modifying the core architecture.

## Unknown information

Missing organizational facts are represented explicitly by the `UNKNOWN` sentinel. EIS must not infer an organizational fact merely because a field is empty or because an agent expects one to exist.

## Retrieval and isolation

`OrganizationStore` provides stable access to organization data and product retrieval. Retrieval can be constrained by product ID or entity kind so information from one product does not silently become context for another product.

Relationships are explicit records rather than implicit agent knowledge.

## Initial data

`src/eis/organization/data.py` contains the initial configuration. It only populates information established in the EIS knowledge base; fields without established information remain `UNKNOWN`.

The configuration is intentionally replaceable. A future persistent database, document-backed configuration, or remote organizational knowledge service can implement `OrganizationStore` without changing specialized agents.
