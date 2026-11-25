# ADR-0001: LangGraph (StateGraph) as the central orchestrator

- **Status:** Accepted
- **Date:** 2026-06-25

## Context

RegWatch is not a linear prompt→response flow. The pipeline needs:

- **Conditional branches** (guardrail blocks / passes; judge approves / retries).
- **Parallel execution** (hybrid retrieval and the tools sub-agent at the same time).
- **Bounded cycles** (analysis retry loop, tools sub-agent loop).
- **Pause and resume** for human-in-the-loop (see [ADR-0011](ADR-0011-human-in-the-loop-interrupt.md)).
- **Typed, shared state** across nodes.

An LCEL chain (`prompt | llm | parser`) is excellent for linear flows, but it does not natively model
branching, cycles or state persistence. Orchestrating this "by hand" with Python functions and
`if/else` would reimplement, and do worse, what LangGraph already provides.

## Decision

Use **LangGraph `StateGraph`** as the central orchestrator. The state is a `TypedDict`
(`RegWatchState`), the nodes are pure functions `state -> dict`, and the control flow is expressed
with `add_edge`, `add_conditional_edges` and a checkpointer for persistence.

## Consequences

**Positive**
- Fan-out/fan-in, conditional edges and cycles are first-class primitives.
- The checkpointer enables HITL (pause/resume) and fault tolerance without extra code.
- The graph is inspectable and can be streamed node by node (feeds the UI).
- Fits the rest of the LangChain stack (tools, models, LangFuse).

**Negative / trade-offs**
- A steeper learning curve than a simple LCEL chain.
- Shared state requires thinking about reducers when two branches write the same key.

## Alternatives considered

- **Pure LCEL chains:** rejected; they do not model branching, cycles or persistence.
- **Manual orchestration in Python:** rejected; it reimplements LangGraph's scheduler with more bugs.
- **Generic agent frameworks (e.g. CrewAI/AutoGen):** rejected; they offer less explicit control of the
  graph and of persistence, which an auditable compliance use case needs.

## References


- Course: Block 6 (LangGraph), Block 4 (LangChain/LCEL).
