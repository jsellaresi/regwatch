# ADR-0008: Structured output with Pydantic

- **Status:** Accepted
- **Date:** 2026-06-25

## Context

The analysis node and the judge must return data that the rest of the graph can consume (gaps with typed fields,
numeric scores). The initial technique, asking for JSON in the prompt and extracting it with
`content.find("{") ... json.loads(...)`, is fragile:

- It breaks if the model wraps the JSON in text, uses markdown fences, or produces invalid JSON.
- A parsing failure raises an exception that **brings down the whole graph**.
- It does not validate types or ranges (e.g. `risk_level` outside {HIGH, MEDIUM, LOW}, `confidence` > 1).

## Decision

Define **Pydantic** schemas (`Gap`, `GapReport`, `JudgeScores`) and use
`llm.with_structured_output(Schema)`. The model is required to return a valid object (it retries internally if the
output does not fit). In addition, each node wraps its body in a `try/except` that writes an `error` field to the
state and routes to a safe end, instead of propagating the exception.

## Consequences

**Positive**
- Type and range validation happens at the boundary (Literal, `ge/le`), not downstream.
- Removes fragile manual parsing and its whole class of bugs.
- The same definition is reused in the analysis, the judge and the eval suite (consistency).
- No node brings down the graph: errors are caught and routed.

**Negative / trade-offs**
- `with_structured_output` may use the provider's tool-calling/function-calling; it adds a little overhead compared
  to plain text (negligible next to the robustness gained).
- Couples the output schema to the code; changing it requires migrating consumers (desirable: it is explicit).

## Alternatives considered

- **Manual JSON parsing (`json.loads`):** rejected for being fragile and for bringing down the graph.
- **`PydanticOutputParser` over text:** better than manual parsing, but `with_structured_output` gives stronger
  guarantees by delegating the format to the provider.

## References

- Code: `graph/schemas.py`, `graph/nodes/analyze_compliance.py`, `graph/nodes/agent_judge.py`.
- Course: Block 4 (parsers), Block 7 (consistent evals).
