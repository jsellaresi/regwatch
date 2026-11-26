# RegWatch — Intelligent Compliance Analysis Platform

Automated gap analysis for European financial regulations (GDPR, MiFID II, AML). Upload an internal policy PDF and receive a structured report with detected gaps, exact regulatory references, and JIRA remediation tickets — in minutes.

Capstone project of an AI Engineering program: a production-style agentic system (LangGraph, hybrid RAG, guardrails, agent-as-judge, human-in-the-loop) with every design decision recorded as an ADR. Use only synthetic documents — do not upload real policies or personal data to the external LLM services.

**Language:** the documentation and code are in English, but the product itself works in Spanish — the regulation corpus (EU texts in Spanish), the analysis prompts, the guardrail and error messages and the UI are Spanish by design.

## Quick Start

```bash
git clone https://github.com/jsellaresi/regwatch.git
cd regwatch
cp .env.example .env          # fill in ANTHROPIC_API_KEY, OPENAI_API_KEY, LANGFUSE_*, ...

docker compose up -d --build

# Seed the RAG corpus and register the prompt (first time only)
docker compose exec api python -m scripts.ingest_regulations
docker compose exec api python -m scripts.register_prompts
```

| Service | URL |
|---|---|
| Frontend (UI) | http://localhost:5173 |
| API (Swagger) | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 (`regwatch` / `regwatch`) |

For full setup instructions, local development without Docker, and how to test all pipeline paths → **[RUNBOOK.md](docs/RUNBOOK.md)**

---

## Architecture

```
PDF Upload → check_cache → multimodal_extract → input_guardrail
                                                     │ fan-out
                              retrieve_regulations ──┤
                                  rerank             │
                              enrich_agent ──────────┘ join
                                               analyze_compliance
                                               output_guardrail
                                               agent_judge
                                               human_review (HITL)
                                               format_report → write_cache → create_tickets → store_episodic_memory
```

Every run passes through human review: the judge only decides whether the analysis is retried first.

**LangGraph** orchestrates the pipeline. **LangFuse** traces every node. **Vue 3** streams live node progress via SSE.

## Project Structure

```
regwatch/
├── config.py                    # env vars, LangFuse client, LLM cache
├── retriever.py                 # hybrid pgvector + BM25 singleton
├── document_store.py            # transient in-memory PDF bytes keyed by sha256
│
├── graph/
│   ├── state.py                 # RegWatchState TypedDict
│   ├── schemas.py               # Gap, GapReport, JudgeScores (Pydantic)
│   ├── builder.py               # StateGraph wiring + get_graph() singleton
│   └── nodes/                   # one file per node
│       ├── cache.py             # check_cache / write_cache
│       ├── multimodal_extract.py
│       ├── guardrails.py        # input + output guardrails
│       ├── retrieve_regulations.py
│       ├── rerank.py            # Cohere Rerank / BGE local
│       ├── enrich_agent.py      # LLM sub-agent + ToolNode loop
│       ├── analyze_compliance.py
│       ├── agent_judge.py       # GPT-4o judge
│       ├── human_review.py      # interrupt() HITL
│       ├── memory.py            # episodic gap tracking
│       ├── format_report.py
│       └── create_tickets.py   # deterministic JIRA
│
├── tools/
│   └── regulation_tools.py      # EUR-Lex, web search, JIRA (@tool)
│
├── api/
│   ├── main.py                  # FastAPI: /analyze, /analyze/stream (SSE), /resume, /chat, /ingest
│   ├── security.py              # X-API-Key check + PDF upload validation
│   └── chat.py                  # /chat question guardrail + delimited prompt
│
├── frontend/
│   └── src/
│       ├── composables/useAnalysis.js
│       └── components/RegWatch.vue
│
├── scripts/
│   ├── ingest_regulations.py    # load PDF corpus into pgvector
│   ├── register_prompts.py      # create/version prompt in LangFuse
│   └── promote_prompt.py        # staging → production
│
├── evals/
│   ├── golden_dataset.py
│   ├── eval_suite.py            # staging prompt vs the golden dataset (precision/recall)
│   ├── retrieval_eval.py        # regulation/article hit rate of retrieval + rerank
│   └── retrieval_suite.py       # retrieval gate tests (thresholds via env vars)
│
├── tests/                       # unit, graph-wiring and live-Postgres tests
├── .github/workflows/           # health-check (lint + tests) and eval-gate
│
├── observability/
│   └── tracing.py               # LangFuse span enrichment + score logging
│
├── migrations/
│   ├── 001_cache.sql            # analysis_cache table
│   ├── 002_memory.sql           # policy_episodes table
│   └── 003_fix_llm_cache.sql    # drops the old LLM cache table (recreated hashed)
│
├── docker/
│   ├── init-db.sql              # CREATE EXTENSION vector
│   └── nginx.conf               # SPA + API proxy (SSE-safe)
│
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml               # dependencies (uv)
└── .env.example
```

## Stack

| Layer | Technology |
|---|---|
| Orchestration | LangGraph (StateGraph + PostgreSQL checkpointer + `interrupt()`) |
| Analysis LLM | `claude-haiku-5-5` |
| Judge LLM | `gpt-4o` |
| Vision LLM | `claude-sonnet-5-5` (multimodal, scanned PDFs) |
| Embeddings | `text-embedding-3-small` (OpenAI) |
| Vector DB | PostgreSQL + pgvector |
| Keyword search | BM25Retriever (rank_bm25) |
| Reranking | Cohere Rerank 3 (or local `BAAI/bge-reranker-v2-m3`) |
| Observability | LangFuse |
| API | FastAPI + SSE streaming |
| Frontend | Vue 3 + Vite |

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | Analysis + Vision |
| `OPENAI_API_KEY` | ✅ | Embeddings + Judge |
| `LANGFUSE_PUBLIC_KEY` | ✅ | Observability |
| `LANGFUSE_SECRET_KEY` | ✅ | Observability |
| `LANGFUSE_HOST` | ✅ | LangFuse endpoint (e.g. `https://cloud.langfuse.com`) |
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `REGWATCH_API_KEY` | ✅ | Key every API request must send in `X-API-Key` (the UI asks for it on load); the API refuses to start without it |
| `MAX_UPLOAD_MB` | ❌ | Max uploaded PDF size (default `20`); non-PDF uploads are rejected |
| `JIRA_API_TOKEN` | ❌ | Ticket creation token (required if `JIRA_ENABLED=true`) |
| `JIRA_ENABLED` | ❌ | Set to `true` to enable JIRA ticket creation (default: `false`) |
| `JIRA_BASE_URL` | ❌ | Your Atlassian instance URL (e.g. `https://acme.atlassian.net`) |
| `COHERE_API_KEY` | ❌ | Reranking (falls back to local BGE if absent) |

## Testing

```bash
uv sync
uv run pytest tests -q        # no env vars, DB or network required
uv run pytest evals/eval_suite.py -q       # staging prompt vs the golden dataset (needs live API keys)
uv run pytest evals/retrieval_suite.py -q  # retrieval + rerank hit rate (needs the corpus ingested, OpenAI key, a reranker)
```

Four layers, from cheapest to most realistic:

| Layer | What it checks | Needs |
|---|---|---|
| Unit tests (`tests/`) | Regexes, routing functions, SQL strings, config, security helpers | nothing |
| Graph wiring (`tests/test_graph_wiring.py`) | The real compiled graph with scripted fakes for LLMs, DB and Langfuse: retries, escalation to human review, blocking, cache short-circuit, PII redaction reaching the prompt | nothing |
| Live Postgres (`tests/test_live_*.py`) | Re-ingestion, HNSW index and the hybrid retriever against a real pgvector database, with fake embeddings | `REGWATCH_TEST_DATABASE_URL` pointing at a disposable database whose name contains `test` (skipped otherwise; the health-check workflow provides one) |
| Eval gate (`evals/`) | Analyzer precision/recall and retrieval hit rate with real models | API keys, the ingested corpus |

CI runs lint and the first three layers on every push and pull request (`.github/workflows/health-check.yml`); the eval gate (`.github/workflows/eval_gate.yml`) ingests the corpus into a pgvector service, runs both eval suites and, only if they pass, promotes the staged prompt.

### CI and secrets

The eval gate calls paid LLM APIs, so it only runs for the repository owner, on `main` or manually, and reads its keys from the `evals` GitHub environment (restricted to `main`). Pull requests from forks never receive secrets, and external contributors' workflows need approval before they run.

## Known limitations

- **Single shared API key.** No per-user identity or rate limiting, and any `thread_id` can be read with the key.
- **Cache hits.** A cache hit returns the stored report of an earlier run verbatim (its `policy_id` and prompt version included) and skips human review, tickets and memory; the key is the document hash alone.
- **Gap identity** is the regulation reference, so two distinct gaps on the same article count as one in the episodic memory.
- **Guardrails** rely on finite pattern lists (Spanish and English injections, DNI/NIE/IBAN/card/SSN) plus an LLM check; paraphrased attacks depend on the LLM check alone. Company tax IDs are not redacted.
- **Uploads** are limited to PDFs up to `MAX_UPLOAD_MB`; a file with a valid header but a corrupt body fails inside extraction.
- **Uploaded PDFs live in process memory** (`document_store.py`) between upload and extraction, so an API restart in that window fails that run with an "upload it again" error.
- **Windows:** `psycopg` async cannot use asyncio's default `ProactorEventLoop`, so the connection pool times out. Run the stack with Docker (Linux) or WSL.
- **`/chat`** calls the LLM synchronously inside an async handler, which blocks the event loop while it answers.
- **Retrieval eval thresholds** (`RETRIEVAL_MIN_REGULATION_HIT`, `RETRIEVAL_MIN_ARTICLE_HIT`) are provisional until calibrated against a real run; the golden dataset has only three evaluable cases, so each rate moves in steps of 0.33. Article attribution relies on each chunk's `articles` tag (set at ingestion from "Artículo N" headers), so a cross-reference at the start of a line can be tagged with the wrong article.
- **The LLM-dependent paths** (analysis, vision, judge, semantic guardrail, chat) are verified only by the eval gate and by manual runs, not by the key-less test layers.
- Model IDs in `config.py` are the previous generation of the Claude family.

## License

[MIT](LICENSE)

## Documentation

- **[docs/GETTING-STARTED.md](docs/GETTING-STARTED.md)** — setup, first run, how to use the UI (start here)
- **[RUNBOOK.md](docs/RUNBOOK.md)** — exhaustive testing paths, fixtures, curl examples
- **[docs/](docs/README.md)** — 14 Architecture Decision Records (the *why* behind each design choice)

| ADR | Decision |
|---|---|
| [ADR-0001](docs/ADR-0001-langgraph-orchestrator.md) | LangGraph as central orchestrator |
| [ADR-0002](docs/ADR-0002-postgres-unified-store.md) | PostgreSQL as unified store |
| [ADR-0003](docs/ADR-0003-hybrid-retrieval.md) | Hybrid retrieval: pgvector + BM25 + RRF |
| [ADR-0004](docs/ADR-0004-hnsw-vector-index.md) | HNSW vector index |
| [ADR-0005](docs/ADR-0005-cross-encoder-reranking.md) | Cross-encoder reranking |
| [ADR-0006](docs/ADR-0006-caching.md) | Caching strategy (result + LLM) |
| [ADR-0007](docs/ADR-0007-two-layer-guardrails.md) | Two-layer guardrails with retry cap |
| [ADR-0008](docs/ADR-0008-structured-output-pydantic.md) | Structured output with Pydantic |
| [ADR-0009](docs/ADR-0009-prompt-versioning-eval-gate.md) | Prompt versioning + CI eval gate |
| [ADR-0010](docs/ADR-0010-agent-as-judge.md) | Agent-as-Judge with a different model |
| [ADR-0011](docs/ADR-0011-human-in-the-loop-interrupt.md) | Human-in-the-loop with `interrupt()` |
| [ADR-0012](docs/ADR-0012-tools-pattern.md) | Tools pattern: gather with LLM, act deterministically |
| [ADR-0013](docs/ADR-0013-episodic-memory.md) | Episodic memory only (no conversational) |
| [ADR-0014](docs/ADR-0014-multimodal-vision.md) | Multimodal extraction with Claude Vision |
