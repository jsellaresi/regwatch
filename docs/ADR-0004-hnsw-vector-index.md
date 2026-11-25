# ADR-0004: HNSW vector index and database indexes

- **Status:** Accepted
- **Date:** 2026-06-25

## Context

Semantic search over pgvector needs an approximate nearest-neighbour (ANN) index; without one, pgvector
does a *full scan* (exact but O(n) per query). pgvector offers two ANN index types:

- **IVFFlat:** partitions the space into `lists` clusters; at query time it probes `probes` clusters.
  Cheap to build, but **requires representative data when the index is created** (it trains the
  centroids), and its recall degrades if the dataset grows or its distribution changes after training.
- **HNSW:** hierarchical navigable graph. Better recall and query latency, more expensive build and
  higher memory use; **requires no prior training** and tolerates incremental inserts.

Besides the embeddings, there are hot relational queries that also need indexes: cache lookup by hash and
lookup of the latest episode per policy.

## Decision

**1. Vector index: HNSW** on the embedding column, with cosine distance:

```sql
CREATE INDEX ON langchain_pg_embedding
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
-- at query time: SET hnsw.ef_search = 40;
```

- `m = 16`: number of connections per node (recall/memory balance, recommended default value).
- `ef_construction = 64`: size of the dynamic list during construction (higher = better graph, slower build).
- `vector_cosine_ops`: cosine, consistent with the normalised OpenAI embeddings (`text-embedding-3-small`).

**Implementation note:** this `CREATE INDEX` does not live in `docker/init-db.sql`. That script runs only
once, on the first container start with an empty data volume, before the app has ever created
`langchain_pg_embedding` (`PGVector` from `langchain_community` creates it lazily, on the first
ingestion). A `CREATE INDEX` there would fail on a new volume, or, if it were guarded to avoid failing,
would never run (init-db.sql does not run again after the first start). The index is created in
`scripts/ingest_regulations.py::_ensure_hnsw_index()`, with `CREATE INDEX IF NOT
EXISTS idx_langchain_pg_embedding_hnsw ...` (explicitly named, because Postgres requires a name for
`IF NOT EXISTS`), invoked right after each `PGVector.from_documents(...)` call. It is idempotent, so running
it once per ingested regulation has no relevant cost.

**2. Relational indexes (B-tree):**

```sql
-- cache lookup by document hash (see ADR-0006)
-- analysis_cache.doc_hash is already PRIMARY KEY → implicit B-tree
-- latest episode per policy (see ADR-0013)
CREATE INDEX idx_policy ON policy_episodes (policy_id, created_at DESC);
```

The composite index `(policy_id, created_at DESC)` directly serves the query "latest report for this
policy" (`WHERE policy_id = ? ORDER BY created_at DESC LIMIT 1`) without a sort.

## Consequences

**Positive**
- HNSW gives better recall/latency than IVFFlat and, crucially, **tolerates incremental re-ingestion**
  of the corpus (regulations get amended) without retraining.
- In compliance, recall matters: an unretrieved article = an undetected gap.
- The B-tree indexes make cache and memory lookups O(log n).

**Negative / trade-offs**
- HNSW uses more memory and builds more slowly than IVFFlat (irrelevant here: the corpus is thousands of
  chunks, not millions).
- `ef_search` is a parameter to tune: higher = more recall and more latency.

## Alternatives considered

- **IVFFlat:** rejected because recall degrades with changing data and because it requires retraining the
  centroids after re-ingestion.
- **No index (exact full scan):** rejected; O(n) per query does not scale even though it is exact.
- **L2 / inner product distance:** rejected in favour of cosine for consistency with normalised embeddings.

## References

- Code: `migrations/002_memory.sql`.
- Course: Block 10 (pgvector, IVFFlat vs HNSW, similarity operators, schema design).
