# ADR-0009: Prompt versioning + eval gate in CI

- **Status:** Accepted
- **Date:** 2026-06-25

## Context

The analysis prompt is a living artifact: it changes when a regulation is amended, when few-shot examples are added,
or when the output format is tuned. Treating it as hardcoded text in the code causes two problems:

1. **No traceability or rollback:** it is not known which prompt version produced a report (bad for audit), and
   reverting requires a code deployment.
2. **No safety net:** a prompt change can silently degrade quality (lower gap recall, worse citations) and nobody
   finds out until production.

## Decision

- **Prompt versioning in LangFuse Prompt Management.** The code requests the prompt by *label* (`production`);
  publishing a version or rolling back is a matter of changing the label, without touching code. The version used is
  recorded in each report's trace (audit).
- **Eval gate in CI.** A *golden* dataset with known cases measures *precision/recall* and citation format.
  GitHub Actions runs the suite against the prompt in `staging`; **only if it passes the thresholds** (precision ≥ 0.85,
  recall ≥ 0.80, 0 malformed citations) is it promoted to `production` (`promote_prompt.py`). The gate also runs a
  retrieval suite (`evals/retrieval_suite.py`): whether the expected regulation and article reach the analyzer after
  retrieval and reranking (provisional thresholds).
- **Registration and promotion.** `register_prompts.py` labels a new version `staging`; only the very first
  registration in an environment also gets `production`, so the app can start. `promote_prompt.py` relabels the
  version that was evaluated as `production` instead of creating a new one, so production runs exactly the version
  that passed the gate.

## Consequences

**Positive**
- Instant rollback and prompt↔report traceability for audit.
- No prompt change reaches production without passing the quality barrier.
- Decouples prompt iteration from the code deployment cycle.

**Negative / trade-offs**
- Dependency on LangFuse as the prompt registry (mitigable: prompts can be exported).
- The golden dataset must be maintained and expanded; a weak golden set gives false confidence.

## Alternatives considered

- **Prompts hardcoded in the code:** rejected; no fast rollback or traceability.
- **Versioning prompts in git without an eval gate:** better than hardcoding, but does not prevent quality regressions.
  The automatic gate is the differentiating value.

## References

- Code: `scripts/register_prompts.py`, `scripts/promote_prompt.py`, `.github/workflows/eval_gate.yml`.
- Course: Block 7 (prompt versioning, evals), Block 18 (CI/CD).
