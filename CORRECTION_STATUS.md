# RegWatch Correction — Progress Tracker

Tracks implementation of `C:\Users\josi\.claude\plans\review-the-code-base-eager-flurry.md`
(the plan built from Javier Carreira's grading PDF, 6.74/10, all 24 findings
re-verified against the live code). Updated as each fix lands. One fix at a
time, each with a unit test where one meaningfully guards it, per instruction.

Legend: ✅ done · 🚧 in progress · ⬜ not started · ➕ discovered mid-fix (not in original plan)

---

## Phase 1 — P0: unblock the happy path

| # | Fix | Status | Tests added |
|---|-----|--------|-------------|
| ➕ | **Import-time side effects blocking unit tests/CI (part 1: config/retriever/rerank)** — `config.py` raised on import without 5 live env vars + built a real Langfuse client + SQLAlchemy engine at import; `retriever.py` ran a live DB query + built `PGVector` at import; `rerank.py` downloaded a CrossEncoder model at import. All three now lazy-loaded on first real use; `config.validate_required()` / `config.init_llm_cache()` called explicitly once at real entry points (`api/main.py` lifespan, scripts' `__main__`, `evals/conftest.py`). Folded in the plan-9 reranker model swap (`MODEL_RERANK_LOCAL` → `BAAI/bge-reranker-v2-m3`) since we were already touching that lazy-load. | ✅ | `tests/test_import_side_effects.py` (3 cases, subprocess-isolated) |
| ➕ | **Import-time side effects, part 2: the last 5 LLM clients** — `guardrails.py`, `analyze_compliance.py`, `enrich_agent.py`, `multimodal_extract.py`, `agent_judge.py` each built a `ChatAnthropic`/`ChatOpenAI` client at module scope, which is why `tests/conftest.py` still needed dummy `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`. Same lazy-getter pattern applied to all 5. Result: `import graph` now needs **zero** env vars, zero DB, zero network, zero model download — confirmed via subprocess with a fully clean environment. `tests/conftest.py` and `tests/__init__.py` deleted entirely; `test_citation_regex.py` uses a plain `from graph.schemas import ...` import. | ✅ | 4th case added to `tests/test_import_side_effects.py`: `test_importing_graph_needs_no_env_vars_at_all` |
| 1 | Unify citation regex (`graph/schemas.py`, guardrail + eval both import it) | ✅ | `tests/test_citation_regex.py` (16 cases) |
| 2 | Fix `/analyze`: `graph.invoke` → `await graph.ainvoke`, handle interrupted state | ✅ | `tests/test_extract_interrupt_payload.py` (6 cases) |
| 3 | Reinject `guardrail_reason`/`critical_issues` into retry `HumanMessage` | ✅ | `tests/test_build_retry_feedback.py` (7 cases) |
| 4 | Fix CI eval gate (env vars, workflow path, trigger filter) | ✅ | `tests/test_ci_eval_gate_collects.py` (3 cases) |
| 5 | Create the HNSW index (relocated from plan's `docker/init-db.sql` to `scripts/ingest_regulations.py` — see note below) | ✅ | `tests/test_hnsw_index_sql.py` (4 cases) |
| 6 | Gate/remove `ensure_prompts()` from startup lifespan | ✅ | `tests/test_no_prompt_registration_on_startup.py` (4 cases) |
| — | `analyze_compliance` exception branch missing `gap_report` key (bundled with #3) | ⬜ | |

## Phase 2 — P1: align code with the "Aceptada" ADRs

| # | Fix | Status | Tests added |
|---|-----|--------|-------------|
| 7 | Cache invalidation on prompt promotion / re-ingest (ADR-0006) | ⬜ | |
| 8 | Wire `log_judge_scores` into `agent_judge.py` (ADR-0010) | ⬜ | |
| 9 | Reranker multilingual model | ✅ *(done early, folded into the infra fix above)* | — |
| 10 | `enrich_agent` tools: real `web_search_regulation`, loud `get_regulation_amendments` failure | ⬜ | |
| 11 | Judge needs `retrieved_regulations`; compute `overall_score`/`approved` in Python | ⬜ | |
| 12 | JIRA auth (Basic, not Bearer), API version, externalize project key | ⬜ | |
| 13 | Dedupe tickets against `memory_diff["new"]` | ⬜ | |
| 14 | Document retrieval query-size limitation in ADR-0004 (decomposition itself deferred) | ⬜ | |
| 15 | Align ADR-0010 model claim with code | ⬜ | |

## Phase 3 — P2: robustness, security, cost

| # | Fix | Status | Tests added |
|---|-----|--------|-------------|
| 16 | Async-pool `cache.py`/`memory.py` instead of raw `psycopg2.connect` | ⬜ | |
| 17 | `pre_delete_collection=True` on re-ingest | ⬜ | |
| 18 | Refresh BM25 after `/ingest` | ⬜ | *`retriever.refresh_hybrid_retriever()` already added as a side effect of the infra fix — not yet wired to the `/ingest` endpoint* |
| 19 | Stop checkpointing `document_bytes`/`extracted_images` in graph state | ⬜ | |
| 20 | API authentication | ⬜ | |
| 21 | Validate upload type/size before `fitz.open` | ⬜ | |
| 22 | Localize guardrails (Spanish injection/PII patterns, redact not block) | ⬜ | |
| 23 | Guardrail the `/chat` endpoint | ⬜ | |
| 24 | Fix eval-suite `precision=1.0` default + staging/production label bug | ⬜ | |
| 25–31 | Minor cleanup batch (ticket IDs, memory gap-key collision, undeclared dep, dead graph edge, vite proxy, ruff warnings, README) | ⬜ | |

## Deferred (explicit follow-up, not in this pass)

- Query decomposition in retrieval (finding 13) — half-day design change.
- Full `tests/` suite as a dedicated pass — individual fixes are seeding `tests/` as they go, but a comprehensive pass (fixtures, coverage config) is still separate.

---

## Notes from fixes so far

- **Fix 5 deviates from the plan's wording**: the plan (following the grader's suggestion) said to add the `CREATE INDEX ... USING hnsw ...` to `docker/init-db.sql`. That file runs via Postgres's `docker-entrypoint-initdb.d`, which fires exactly once, on a completely empty data volume — before the app has ever run and before `PGVector` (langchain) has lazily created `langchain_pg_embedding`. Placing the index DDL there would fail outright on a fresh volume, or (if defensively guarded on table existence) silently never create the index at all, since `init-db.sql` never runs again after that first boot. Implemented instead in `scripts/ingest_regulations.py::_ensure_hnsw_index()`, called right after each `PGVector.from_documents(...)` — idempotent (`CREATE INDEX IF NOT EXISTS`, explicitly named since Postgres requires a name for that clause). ADR-0004 updated with an implementation note explaining this, so the ADR keeps matching the real code.
- **Fix 4 deviates from the plan's wording**: the plan (written from the grader's pre-verification snapshot) called for adding a `services: postgres` block to CI, because at the time `config.py` built a live DB-backed LLM cache at import. That root cause was already removed by the earlier import-side-effects fix (part 1), so `evals/eval_suite.py`'s current code path (direct LLM call, no retrieval/rerank/cache) genuinely doesn't touch Postgres — `DATABASE_URL` only needs to be *present* to satisfy `config.validate_required()`, hence a placeholder value in the workflow's `env:` block, with a comment flagging that this needs to become real if evals are ever extended to exercise caching or the full graph.
- The workflow was also moved: real repo root is `Block 20` (where `.git` lives); it previously sat at `regwatch/.github/workflows/`, one level too deep for GitHub Actions to ever discover it. Now at `Block 20/.github/workflows/eval_gate.yml`, alongside the pre-existing unrelated `python-app.yml` (left untouched — not regwatch's concern). **Correction after the fact:** the file's internal `working-directory`/`paths` were initially left as `Block 20/regwatch/...`, which double-counts the prefix since `Block 20` *is* the repo root — corrected to plain `regwatch/...`.

- **`tests/` needs no conftest at all.** After part 2 of the import-side-effects fix (lazy-loading the last 5 LLM clients), `import graph` needs zero env vars, zero DB, zero network, zero model download. `tests/conftest.py` and `tests/__init__.py` were deleted; test files use plain imports (`from graph.schemas import ...`).
- **`evals/conftest.py` still exists, deliberately** — evals genuinely call the live LLM and fetch prompts from Langfuse, so it calls `config.validate_required()` to fail fast with one clear message instead of a confusing error mid-run.
- Plain `import graph.anything` now works with a fully clean environment — confirmed both via direct subprocess and via pytest (`tests/test_import_side_effects.py::test_importing_graph_needs_no_env_vars_at_all`).
