# ADR-0012: Tools pattern — gathering with an LLM vs acting deterministically

- **Status:** Accepted
- **Date:** 2026-06-25

## Context

RegWatch has three external capabilities (tools):

- `get_regulation_amendments` (EUR-Lex) and `web_search_regulation`: **gather information**.
- `create_jira_ticket`: **performs an action** with side effects (opens a real ticket).

A common design mistake is to expose all tools to an LLM agent and let it "decide" what to do, including
the action. In compliance, letting a model decide *whether* to open a ticket (or how many) is risky: the
effects are non-deterministic and hard to audit and test.

(Note: the initial version also had a bug — a standalone `ToolNode` with no LLM generating `tool_calls`
and no `messages` key in the state; the tools were never executed.)

## Decision

Separate tools by intent:

- **Gather → with an LLM.** A sub-agent `enrich_agent` with `bind_tools(ENRICH_TOOLS)` decides which
  information tools to call and with which arguments, in an `enrich_agent ⇄ ToolNode` loop until there are
  no more `tool_calls`. This requires the `messages` key (`add_messages`) in the state.
- **Act → deterministic.** `create_jira_ticket` is **not** exposed to the LLM. The `create_tickets` node
  iterates over the HIGH/MEDIUM gaps and invokes the tool directly, in a predictable and auditable way.

## Consequences

**Positive**
- The open-ended, exploratory part (which external information to fetch) benefits from the LLM's flexibility.
- The part with side effects is deterministic: testable, auditable, no surprises.
- Information tools **are now executed** (correct loop with `messages`), fixing the bug.
- `enrich_agent` runs in parallel with retrieval (fan-out) and joins at the analysis step.

**Negative / trade-offs**
- Two different mechanisms for "using tools" in the same system (the distinction has to be understood).
- The sub-agent's loop adds LLM calls when it decides to query external sources.

## Alternatives considered

- **A single agent with all tools (including JIRA):** rejected; it hands control of an action with side
  effects to the LLM, which is bad for auditing and testing.
- **Everything deterministic (no sub-agent):** rejected; it would lose the flexibility to decide when to
  enrich with amendments/search depending on the document.

## References

- Code: `tools/regulation_tools.py`, `graph/nodes/enrich_agent.py`.
- Course: Block 4 (LangChain tools), Block 6 (ToolNode + agentic loop).
