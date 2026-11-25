# ADR-0002: PostgreSQL as the unified store

- **Status:** Accepted
- **Date:** 2026-06-25

## Context

RegWatch needs to persist four very different kinds of data:

1. **Embeddings** of the regulatory corpus for RAG (vector search).
2. **Checkpoints** of the LangGraph graph (for HITL and recovery).
3. **Cache** of analysis results and LLM calls.
4. **Episodic memory** (report history per policy).

One option is to use a specialised component per need: a dedicated vector DB (Pinecone,
Weaviate), Redis for caching, and another store for checkpoints. That multiplies the infrastructure,
the points of failure and the operational cost for a mid-sized team.

## Decision

Use **PostgreSQL as a single store** for all four needs:

- **pgvector** for embeddings and similarity search (see [ADR-0004](ADR-0004-hnsw-vector-index.md)).
- **`PostgresSaver`** from LangGraph for checkpoints.
- `analysis_cache` table (result cache) + `SQLAlchemyCache` (LLM cache).
- `policy_episodes` table for episodic memory.

## Consequences

**Positive**
- A single engine to operate, back up and monitor; less lock-in than a proprietary vector DB.
- Transactionality and joins between relational and vector data when needed.
- pgvector is sufficient in precision and latency for the size of this corpus (see ADR-0004).
- Predictable cost; trivial deployment on RDS/Cloud SQL (Block 16).

**Negative / trade-offs**
- Postgres does not match a dedicated vector DB for collections of hundreds of millions of vectors
  (not the case here: the regulatory corpus is thousands of chunks).
- Caching in Postgres has more latency than an in-memory Redis; acceptable because the result cache
  avoids a ~12 s pipeline and the LLM cache only deduplicates retries.

## Alternatives considered

- **Dedicated vector DB (Pinecone/Weaviate) + Redis + checkpoint store:** rejected as
  over-engineering for the volume and because it multiplies infrastructure.
- **In-memory only / files:** rejected; it does not survive restarts and does not support persistent HITL.

## References

- Code: `migrations/001_cache.sql`, `002_memory.sql`.
- Course: Block 10 (PostgreSQL + pgvector, unified stack).
