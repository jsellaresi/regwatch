# ADR-0011: Human-in-the-loop with `interrupt()`

- **Status:** Accepted
- **Date:** 2026-06-25

## Context

The judge ([ADR-0010](ADR-0010-agent-as-judge.md)) may repeatedly reject a report. The initial design
handled this with `judge_passed = approved or attempt >= 3`: that is, after 3 attempts it **auto-approved**
a report the evaluator had rejected three times. In a compliance system this is unacceptable: a
low-quality report would be issued and JIRA tickets opened on unreliable conclusions, without any human
knowing.

When automation does not reach the minimum quality, **a person must decide**, and the system must be able
to **pause** while waiting for that decision, potentially for minutes or hours, without keeping a process
blocked in memory.

## Decision

Replace the force-pass with a `human_review_checkpoint` node that uses LangGraph's **`interrupt()`**:

- When the judge exhausts its retries (or the output guardrail exhausts its own), the graph routes to
  `human_review_checkpoint`, which calls `interrupt({...})` with the report and the scores.
- `interrupt()` **stops the graph and persists its state** via the Postgres checkpointer
  ([ADR-0002](ADR-0002-postgres-unified-store.md)). The process is not blocked: the run ends and can be
  resumed later.
- The officer reviews (in the UI) and the API resumes with
  `graph.invoke(Command(resume="approve"|"reject"), config)` on the same `thread_id`.
- `approve` → `format_report` (or, if the analysis itself failed, a final error report: nothing is cached, ticketed
  or remembered); `reject` → retries the analysis.

## Why `interrupt()` and not other forms of "pausing"

- A plain `input()` or blocking the thread is **not** an option: the pause can last hours and must survive
  server restarts.
- `interrupt()` + checkpointer materialises the state in Postgres, so resumption is *stateless* from the
  process's point of view: any worker can pick up the `thread_id`.
- It is LangGraph's native primitive for HITL; reinventing it with queues/flags would be more fragile.

## Consequences

**Positive**
- No report rejected by the judge is ever issued automatically; a human always validates it.
- The pause is durable and resistant to restarts (state in Postgres), not a thread waiting around.
- Resumption can be distributed by `thread_id`; it fits the UI's SSE streaming.

**Negative / trade-offs**
- Requires a persistent checkpointer to be configured (already a requirement of ADR-0002).
- The UI/API must manage the "pending review" state and expose approve/reject.

## Alternatives considered

- **Force-pass after N attempts:** rejected; it auto-approves unreliable reports (the original bug).
- **Fail and abort the run:** rejected; it loses the work already done and does not allow intervention.
- **External queue + manual flag:** rejected; it reimplements, less well, what `interrupt()` + checkpointer
  provide.

## References

- Code: `graph/nodes/human_review.py`, `Command(resume=...)`.
- Course: Block 6 (LangGraph HITL, checkpoints), Block 12 (HITL approval nodes).
