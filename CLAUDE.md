# CLAUDE.md (regwatch)

Scoped to this subproject; see `../CLAUDE.md` for the parent-level rules that still apply.

## Correction workflow rules

1. When applying a fix from `C:\Users\josi\.claude\plans\review-the-code-base-eager-flurry.md`,
   add a unit test alongside it whenever one can meaningfully guard the fix (pure logic, regex,
   routing, key derivation, import behavior, etc.). Skip it only when a fix has no testable
   surface (e.g. a doc-only ADR alignment) — say so rather than skipping silently.
2. After each fix (and any fix-adjacent discovery made along the way), update
   `CORRECTION_STATUS.md` before moving to the next fix.
