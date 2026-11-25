# ADR-0013: Episodic memory only (not full conversational memory)

- **Status:** Accepted
- **Date:** 2026-06-25

## Context

"Adding memory" to an LLM system can mean several things (Block 5 and Block 10): a full conversation
buffer, a compressed summary, or episodic/long-term memory. RegWatch's core pipeline is a **single-shot**
analysis of a document: there is no conversation to remember across turns. Putting a full conversation
buffer into the graph state would bloat it without adding value.

There is, however, a real compliance need that **does** require memory: when a **corrected version** of a
policy is resubmitted, the compliance officer wants to know which gaps were resolved, which remain open,
and which are new (*regression tracking*).

## Decision

Implement **long-term episodic memory only**, not conversational memory:

- `policy_episodes` table (Postgres): each approved report is stored per `policy_id`.
- `diff_with_memory` (inside `format_report`) compares the current report with the latest episode for that
  policy and labels each gap as **resolved / still open / new**.
- `store_episodic_memory` is the penultimate node: it persists the approved report as a new episode.

For the UI's **follow-up chat** a lightweight **session buffer** is used, but it lives in the API
(`SESSION_BUFFER`), **not** in the graph state, so as not to pollute the core pipeline.

## Consequences

**Positive**
- Provides *regression tracking* across resubmissions, a real compliance need, reusing the existing
  Postgres/pgvector infrastructure ([ADR-0002](ADR-0002-postgres-unified-store.md)).
- The graph state stays bounded (no conversation histories).
- Clear separation: business memory (episodic, in the graph) vs. chat UX (session, in the API).

**Negative / trade-offs**
- A gap's identity is approximated by `regulation_ref + truncated description`; large rewording of the same
  gap could be counted as "new". Sufficient for this case; tunable.
- Requires a stable `policy_id` as the policy's key (provided by the client on upload).

## Alternatives considered

- **Full conversation buffer in the graph:** rejected; unnecessary for a single-shot flow and it bloats the
  state.
- **Compressed summary (summary memory):** rejected; the document is already the source, so it would be
  redundant.
- **No memory:** rejected; regression tracking across versions of a policy would be lost.

## References

- Code: `graph/nodes/memory.py`, `migrations/002_memory.sql`.
- Course: Block 5 (memory types), Block 10 (episodic memory in PostgreSQL).
