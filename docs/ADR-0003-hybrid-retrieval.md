# ADR-0003: Hybrid retrieval (pgvector + BM25 with Reciprocal Rank Fusion)

- **Status:** Accepted
- **Date:** 2026-06-25

## Context

The analyser needs to retrieve the regulatory articles relevant to a policy. Two kinds of query coexist:

- **Semantic:** "almacenamos datos indefinidamente" (we store data indefinitely) must find the
  *storage limitation* principle (*limitación del plazo de conservación*) even though it shares no exact
  words with it. Vector search handles this.
- **Exact lexical:** references such as "Art. 17" or precise legal terms ("responsable del
  tratamiento", data controller) where an exact match matters. Here vector search sometimes fails and BM25
  succeeds.

Using only one of the two leaves cases uncovered.

## Decision

Combine **semantic search (pgvector)** and **lexical search (BM25)** through an `EnsembleRetriever` with
**Reciprocal Rank Fusion** (50/50 weights). Both retrieve k=20, and the fusion produces the set that the
reranking ([ADR-0005](ADR-0005-cross-encoder-reranking.md)) then refines.

Related decision: BM25 is built **once at startup** over **the same chunks** already embedded (read from
pgvector), not over the raw PDFs on every request. This guarantees that both retrievers operate on an
identical corpus and removes a per-request cost.

## Consequences

**Positive**
- Coverage of both semantic queries and exact matches (citations, legal terms).
- RRF is robust: it does not require calibrating scores across heterogeneous systems, only ranks.
- Single BM25 build → low per-request latency and a consistent corpus.

**Negative / trade-offs**
- Maintaining two indexes (vector + in-memory BM25) uses somewhat more process RAM.
- The in-memory BM25 must be rebuilt if the corpus changes (re-ingestion → restart or reload).

**Query decomposition (implemented):** `graph/nodes/retrieve_regulations.py` initially used
`extracted_text[:2000]` as the *only* query: the first 2,000 characters of the policy document, embedded
in one go. When a policy mixes several topics (data protection, MiFID suitability, KYC/AML) in different
sections, or when the text relevant to a gap falls after character 2,000, that text never made it into
the k=20 candidate set at all. An unretrieved article is an undetected gap, not a harmless "false
negative" in compliance.

Fixed by splitting the document into queries per section/clause with `RecursiveCharacterTextSplitter`
(separators `"\nSección"`, `"\nSection"`, `"\nCláusula"`, `"\nClause"`, `"\n\n"`, `"\n"` — the same package
`scripts/ingest_regulations.py` already uses to chunk the corpus's regulations), invoking
`get_hybrid_retriever().invoke(query)` once per section (cap of `MAX_SECTIONS = 8` for cost/latency), and
deduplicating the combined result by `(regulation, content)`. A document that fits in a single query
(`<= 2,000` characters) still makes exactly one retrieval call — behaviour unchanged for short documents.
The reranking ([ADR-0005](ADR-0005-cross-encoder-reranking.md)) still reduces the now more diverse set to
`TOP_N = 5` without changes of its own: decomposition improves what enters the candidate *pool*, not how
it is trimmed at the end. If five chunks still fail to cover all the topics of a complex policy after this
fix, raising `TOP_N` is a pending tuning adjustment, not part of this ADR.

## Alternatives considered

- **Semantic only (pgvector):** rejected; it fails on exact citations/terms.
- **Lexical only (BM25):** rejected; it does not capture synonyms or paraphrases.
- **Weighted fusion of normalised scores:** rejected in favour of RRF because of the difficulty of comparing
  score scales between vector search and BM25.

## References

- Code: `retriever.py`, `graph/nodes/retrieve_regulations.py`.
- Course: Block 11 (RAG), Block 12 (Advanced RAG: hybrid retrieval).
