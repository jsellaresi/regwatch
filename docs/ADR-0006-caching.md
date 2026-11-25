# ADR-0006: Caching strategy (result + LLM)

- **Status:** Accepted
- **Date:** 2026-06-25

## Context

A full RegWatch analysis costs ~12 s and ~$0.04 (multimodal extraction + retrieval + rerank +
analysis + judge, with possible retries). Two spending patterns are avoidable:

1. **The same document is re-analyzed** (an officer reopens the case, an identical PDF is resubmitted). Repeating
   the whole pipeline is pure waste.
2. **Identical LLM calls within the same run** (analysis retries, running the eval suite) recompute the same
   response.

## Decision

Two complementary cache layers:

1. **Result cache** (`analysis_cache`): first node of the graph (`check_cache`). Key = `sha256(document_bytes)`.
   If a **current** report exists (TTL = 7 days), it short-circuits and is returned without running anything else.
   `write_cache` persists it after `format_report`.
2. **LLM cache** (`set_llm_cache(SQLAlchemyCache(...))`): deduplicates identical model calls during retries and evals.

**Invalidation** (key for correctness in compliance): clear/expire the result cache when (a) a new prompt version is
promoted ([ADR-0009](ADR-0009-prompt-versioning-eval-gate.md)), or (b) a regulation is re-ingested. An old report
could be based on outdated regulatory text. The 7-day TTL is a second safeguard in case explicit invalidation fails.

## Consequences

**Positive**
- Repeated documents: near-instant response and ~zero cost.
- The LLM cache makes retries and evals cheaper without extra logic in the nodes.
- Byte-level hashing: if the PDF changes by a single byte, the key changes and an outdated result is never served.

**Negative / trade-offs**
- Risk of serving an outdated report if invalidation is forgotten; mitigated by the TTL plus invalidation on the two
  events that change its semantics (prompt and corpus).
- A Postgres cache adds some latency compared to Redis; acceptable given what it saves.

## Alternatives considered

- **No cache:** rejected; unnecessary cost and latency on re-analysis.
- **Redis cache:** valid, but adds infrastructure; Postgres is preferred for unification
  ([ADR-0002](ADR-0002-postgres-unified-store.md)). Migratable if volume requires it.
- **Key by file name or `policy_id`:** rejected; two different PDFs could collide, or the same name could change
  content. The byte hash is the correct identity.

## References

- Code: `graph/nodes/cache.py`, `config.py` (set_llm_cache), `migrations/001_cache.sql`.
- Course: Block 10 (response cache with TTL).
