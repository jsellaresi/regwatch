# ADR-0007: Two-layer guardrails with a retry cap

- **Status:** Accepted
- **Date:** 2026-06-25

## Context

The system receives arbitrary documents uploaded by users and produces reports that are cited as the basis for
compliance decisions. Two risks:

- **Input:** attempts at *prompt injection* or at extracting personal data (PII), or content that is not a corporate
  policy.
- **Output:** **hallucinated or malformed** regulatory citations (e.g. "GDPR Artículo diecisiete" (GDPR Article
  seventeen) instead of "GDPR Art. 17") that would break legal traceability.

An LLM-only check is flexible but expensive and slow for every obvious case; a regex-only check is fast but blind to
semantic attacks. Moreover, an output guardrail that retries the analysis without limit can enter an infinite loop
and drive up cost.

## Decision

**Two-layer guardrails:**

- **Input:** layer 1, a *fast-path* regex check (known injection and PII patterns) → if it does not fire, layer 2,
  a *semantic check* with a cheap LLM (`claude-haiku`). If it blocks, the graph goes to `blocked_end`.
- **Output:** validation of the citation format with regex over the `gap_report`.

**Retry cap:** the output guardrail carries an `output_guardrail_attempt` counter. After 2 failed retries, instead of
retrying further it **escalates to human review** ([ADR-0011](ADR-0011-human-in-the-loop-interrupt.md)).

## Consequences

**Positive**
- The fast-path resolves obvious cases at no LLM cost; the semantic check covers the subtle ones.
- The retry cap eliminates the risk of an infinite loop and runaway cost.
- The output never emits citations in an invalid format without first going through correction or human review.

**Negative / trade-offs**
- The semantic check adds a (cheap) LLM call on the input path.
- Regex patterns require maintenance as new injection techniques appear.

## Alternatives considered

- **Regex only:** rejected; does not detect semantic attacks or out-of-domain content.
- **LLM only:** rejected; more expensive/slower for the trivial cases that regex already filters.
- **Retry without limit until a valid citation:** rejected; infinite loop and cost. It is bounded and escalated instead.

## References

- Code: `graph/nodes/guardrails.py`.
- Course: Block 2 (prompt safety), Block 6 (conditional edges).
