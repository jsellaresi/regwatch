# Architecture Decision Records — RegWatch

This directory records the **architecture decisions** (ADRs) of the RegWatch system, the
compliance-analysis platform.

Each ADR documents the *why* of a decision: the context, the chosen option, its consequences and the
rejected alternatives. Format based on [MADR](https://adr.github.io/madr/).

> **New to RegWatch?** Start with [GETTING-STARTED.md](GETTING-STARTED.md) for setup and usage.

## Index

| #    | Decision | Status |
|------|----------|--------|
| [0001](ADR-0001-langgraph-orchestrator.md) | LangGraph (StateGraph) as the central orchestrator | Accepted |
| [0002](ADR-0002-postgres-unified-store.md) | PostgreSQL as the unified store (pgvector + checkpoints + cache + memory) | Accepted |
| [0003](ADR-0003-hybrid-retrieval.md) | Hybrid retrieval: pgvector + BM25 with Reciprocal Rank Fusion | Accepted |
| [0004](ADR-0004-hnsw-vector-index.md) | HNSW vector index and database indexes | Accepted |
| [0005](ADR-0005-cross-encoder-reranking.md) | Reranking with a cross-encoder | Accepted |
| [0006](ADR-0006-caching.md) | Caching strategy (result + LLM) | Accepted |
| [0007](ADR-0007-two-layer-guardrails.md) | Two-layer guardrails with a retry cap | Accepted |
| [0008](ADR-0008-structured-output-pydantic.md) | Structured output with Pydantic | Accepted |
| [0009](ADR-0009-prompt-versioning-eval-gate.md) | Prompt versioning + eval gate in CI | Accepted |
| [0010](ADR-0010-agent-as-judge.md) | Agent-as-Judge with a different model | Accepted |
| [0011](ADR-0011-human-in-the-loop-interrupt.md) | Human-in-the-loop with `interrupt()` | Accepted |
| [0012](ADR-0012-tools-pattern.md) | Tools pattern: gather with an LLM vs act deterministically | Accepted |
| [0013](ADR-0013-episodic-memory.md) | Episodic memory only (not conversational) | Accepted |
| [0014](ADR-0014-multimodal-vision.md) | Multimodal extraction with Claude Vision | Accepted |

## Conventions

- **Possible statuses:** Proposed · Accepted · Rejected · Superseded by ADR-NNNN.
- ADRs are **immutable**: if a decision changes, a new ADR is created that supersedes the previous one.
- Sequential four-digit numbering. The date is the acceptance date.
