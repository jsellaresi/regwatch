# ADR-0010: Agent-as-Judge with a different model

- **Status:** Accepted
- **Date:** 2026-06-25

## Context

The quality of a compliance report cannot be guaranteed by the model that generates it alone: LLMs tend to evaluate
their own output favorably (self-complacency bias). An automatic, objective quality control is needed before the
report is issued or tickets are opened.

## Decision

Introduce an **Agent-as-Judge** node that scores the report on three dimensions (`legal_accuracy`,
`citation_quality`, `actionability`) and decides `approved`. Two key decisions:

1. **A different model from the analyzer:** the analyzer uses `claude-haiku-5-5`; the judge uses `gpt-4o`. An
   independent evaluator reduces the bias of evaluating one's own reasoning.
2. **Structured output** (`JudgeScores`, see [ADR-0008](ADR-0008-structured-output-pydantic.md)) and a **bounded**
   retry loop (max. 3): if it does not approve, the analysis is retried; when attempts are exhausted, the step is
   **not forced** but escalated to human review ([ADR-0011](ADR-0011-human-in-the-loop-interrupt.md)).

The judge's scores are recorded as metrics in LangFuse per trace (observability and tracking per prompt version).

## Consequences

**Positive**
- Objective quality control before issuing; fewer poor reports in production.
- An independent model → evaluation less biased than a self-check.
- The scores feed the dashboard and make it possible to detect regressions per prompt version.

**Negative / trade-offs**
- Cost and latency of a second LLM call per analysis (and per retry).
- Dependency on a second provider (OpenAI) in addition to Anthropic.

## Alternatives considered

- **No judge (trust the analyzer):** rejected; no automatic quality control.
- **Self-evaluation with the same model:** rejected because of self-complacency bias.
- **Offline evals only (no judge at runtime):** the evals (ADR-0009) protect the *prompt*, but do not evaluate
  *each concrete report*; the runtime judge is complementary, not a substitute.

## References

- Code: `graph/nodes/agent_judge.py`.
- Course: Block 7 (LLM-as-a-Judge), Block 9 (multi-provider).
