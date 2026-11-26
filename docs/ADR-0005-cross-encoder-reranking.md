# ADR-0005: Reranking with a cross-encoder

- **Status:** Accepted
- **Date:** 2026-06-25

## Context

The hybrid retrieval ([ADR-0003](ADR-0003-hybrid-retrieval.md)) returns a reasonable top-k, but ordered by
a rank fusion (RRF), not by true relevance evaluated jointly over query and document. Bi-encoders
(embeddings) encode query and document separately and lose interaction nuances.

In compliance, **context precision is critical**: if the truly relevant article does not make it into the
top that is passed to the analyser, the citation will be wrong and the judge's `legal_accuracy` metric will
drop. Passing many chunks "just in case" is not free either: it inflates tokens, cost and latency, and
dilutes the model's attention.

## Decision

Add a `rerank` node with a **cross-encoder** that reorders the hybrid result and keeps the **top-8**
(`TOP_N`). The pattern is: **retrieve k=20 (hybrid) → rerank → top-8 to the analyser**.

Chunks that belong to no article (recitals, annexes) are left out before reranking: they cannot ground a
"Reg Art. N" citation, yet scored high enough to take slots from the articles themselves. Chunks without the
`articles` tag (a corpus ingested before tagging) are kept. The analyzer and the judge read the same
`REG_CONTEXT_CHARS` of regulation text, sized to hold `TOP_N` full chunks.

- **Primary:** Cohere Rerank (`rerank-multilingual-v3.0`, multilingual because the corpus is in Spanish).
- **Local alternative:** `BAAI/bge-reranker-v2-m3` (no per-call cost; requires GPU/CPU).

## Consequences

**Positive**
- Directly raises `legal_accuracy`: the correct article ends up at the top.
- **Net LLM cost goes down:** 8 chunks are passed instead of 10–20 → fewer input tokens to the analyser,
  which is the most expensive call in the pipeline.
- Retrieving broadly (k=20) and refining avoids the dilemma "small k loses recall / large k adds noise".

**Negative / trade-offs**
- Added latency: ~100–400 ms with hosted Cohere; ~1–2 s with local BGE on CPU.
- Cohere introduces cost and an external dependency (~$2 / 1,000 searches). The local alternative removes
  this in exchange for infrastructure.

## Alternatives considered

- **No reranking (use the top of the hybrid result):** rejected; lower precision in a domain where a wrong
  article is a serious error.
- **Raise k and pass everything to the LLM:** rejected; more cost and latency and a worse signal-to-noise
  ratio than rerank + top-8.
- **LLM-based reranking (listwise via prompt):** rejected because of cost and latency compared with a
  specialised cross-encoder.

## References

- Code: `graph/nodes/rerank.py`.
- Course: Block 12 (Advanced RAG: reranking).
