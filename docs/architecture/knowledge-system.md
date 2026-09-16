# EIS Knowledge System

## Purpose

The knowledge system is the canonical, traceable representation of Echowavs knowledge. It is deliberately independent of LLMs, vector databases, SQL databases, Git providers, and cloud infrastructure.

## Canonical model

A `KnowledgeEntity` represents one identifiable item of organizational knowledge. Its `KnowledgeKind` identifies the domain: company, division, product, project, repository, architecture, engineering standard, business rule, decision, terminology, documentation, workflow, policy, or historical knowledge.

An entity contains:

- stable UUID identity
- name and optional description
- structured (`dict`) or unstructured (`str`) content
- metadata
- explicit directed relationships
- immutable version history
- a current version pointer

## Provenance

Every version carries `Provenance`, which points to a `KnowledgeSource`. A source records its type, locator, optional title and authority, and source metadata. Provenance also records capture time, optional source version, optional content hash, and the ingestion actor.

No canonical knowledge version should exist without provenance. This makes every important fact traceable to its origin.

## Staleness and invalidation

Versions are either `active` or `invalidated`. Normal retrieval and search exclude entities whose current version is invalidated. Historical records remain available only when the caller explicitly requests invalidated knowledge. Invalidating a record therefore cannot silently leave stale information looking authoritative.

An update creates a new version instead of overwriting history. Previous versions and their provenance remain intact.

## Relationships

`KnowledgeRelationship` connects entities using an explicit relation such as `contains`, `depends_on`, `documents`, or `supersedes`. Relationships are data, not implicit assumptions in application code.

## Storage boundary

`KnowledgeRepository` is the stable storage contract. The initial `LocalKnowledgeRepository` is an in-memory development implementation. Future SQL, document, graph, vector, or hybrid implementations can satisfy the same contract without changing canonical models.

## Ingestion boundary

`KnowledgeIngestor` and `KnowledgeSourceConnector` define the source integration boundary. Future GitHub, filesystem, documentation, and database connectors produce normalized `KnowledgeInput` objects. They do not leak provider-specific models into the core.

## Authority rule

A source being recent does not automatically make it authoritative. Authority is metadata that can later participate in explicit conflict-resolution policy. Until such policy exists, EIS must preserve provenance and uncertainty rather than silently choosing between conflicting sources.
