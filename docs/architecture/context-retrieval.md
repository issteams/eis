# Context and Retrieval Engine

Phase 6 provides the boundary between EIS information sources and agent execution. It finds relevant evidence, ranks it, and returns structured context without collapsing provenance into an opaque prompt string.

## Pipeline

`raw query -> normalization -> source retrieval -> metadata filtering -> relevance scoring -> source prioritization -> deduplication -> context ranking -> size management -> ContextResult`

### Query normalization

`QueryNormalizer` lowercases and whitespace-normalizes queries, removes common lexical stopwords, and emits a stable `Query` containing the original input, normalized text, and unique terms.

### Retrieval

`Retriever` is the stable asynchronous retrieval contract. `KeywordRetriever` provides deterministic lexical retrieval. `SemanticRetriever` defines the future embedding/vector boundary without coupling EIS to a vector database or model provider. A hybrid implementation can combine both contracts later.

### Sources

`SourceKind` distinguishes knowledge, memory, project context, repositories, documentation, decisions, and previous tasks. Each `ContextItem` contains a `ProvenanceRecord` with source identity, locator, authority, capture time, version, and metadata.

Authoritative knowledge and decisions can therefore outrank lower-confidence memory without deleting or hiding conflicting evidence. Conflicting content remains separate unless it is an exact duplicate.

### Ranking

Ranking combines lexical relevance, provenance authority, freshness, and source priority. Knowledge and explicit decisions receive higher source priority than transient memory and historical task context. This is a ranking policy, not a claim that every item from a source type is correct.

### Filtering and deduplication

Metadata filters are applied before scoring. Exact normalized content duplicates collapse to the item with stronger authority and score, while semantically or factually conflicting content is preserved because provenance differs.

### Context limits

`ContextRequest.max_characters` bounds assembled context and `limit` bounds item count. `ContextBuilder` returns a `ContextResult` containing structured items and a `truncated` flag. Callers can inspect each item's provenance rather than receiving an untraceable text blob.

## Future vector and hybrid retrieval

The semantic interface intentionally accepts the same normalized query and metadata constraints as lexical retrieval. Future adapters can perform embedding search, sparse/dense hybrid search, reranking, or external vector-store retrieval without changing `ContextBuilder` or the provenance model.

## Staleness

Freshness is represented independently from authority. An authoritative source can become stale, while a recent memory remains lower-confidence. Retrieval ranking considers both dimensions, and source capture/version metadata remains available to downstream integrity and reasoning systems.
