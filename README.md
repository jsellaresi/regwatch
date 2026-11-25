# RegWatch — Intelligent Compliance Analysis Platform

Automated gap analysis for European financial regulations (GDPR, MiFID II, AML). Upload an internal policy PDF and receive a structured report with detected gaps, exact regulatory references, and JIRA remediation tickets — in minutes.

Capstone project of an AI Engineering program: a production-style agentic system (LangGraph, hybrid RAG, guardrails, agent-as-judge, human-in-the-loop) with every design decision recorded as an ADR. Use only synthetic documents — do not upload real policies or personal data to the external LLM services.

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
│   └── main.py                  # FastAPI: /analyze, /analyze/stream (SSE), /resume, /chat
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
│   └── eval_suite.py            # pytest CI gate (precision/recall thresholds)
│
├── observability/
│   └── tracing.py               # LangFuse span enrichment + score logging
│
├── migrations/
│   ├── 001_cache.sql            # analysis_cache table
│   └── 002_memory.sql           # policy_episodes table
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
| Analysis LLM | `claude-haiku-4-5` |
| Judge LLM | `gpt-4o` |
| Vision LLM | `claude-sonnet-4-6` (multimodal, scanned PDFs) |
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
uv run pytest tests -q        # unit tests: no env vars, DB or network required
uv run pytest evals -q        # eval suite against the golden dataset (needs live API keys)
```

CI runs lint and unit tests on every push (`.github/workflows/health-check.yml`) and gates prompt promotion on the eval suite (`.github/workflows/eval_gate.yml`).

## License

[MIT](LICENSE)

## Documentation

- **[docs/GETTING-STARTED.md](docs/GETTING-STARTED.md)** — setup, first run, how to use the UI (start here)
- **[RUNBOOK.md](docs/RUNBOOK.md)** — exhaustive testing paths, fixtures, curl examples
- **[docs/](docs/README.md)** — 14 Architecture Decision Records (the *why* behind each design choice)

| ADR | Decision |
|---|---|
| [ADR-0001](docs/ADR-0001-langgraph-orquestador.md) | LangGraph as central orchestrator |
| [ADR-0002](docs/ADR-0002-postgres-almacen-unificado.md) | PostgreSQL as unified store |
| [ADR-0003](docs/ADR-0003-recuperacion-hibrida.md) | Hybrid retrieval: pgvector + BM25 + RRF |
| [ADR-0004](docs/ADR-0004-indice-vectorial-hnsw.md) | HNSW vector index |
| [ADR-0005](docs/ADR-0005-reranking-cross-encoder.md) | Cross-encoder reranking |
| [ADR-0006](docs/ADR-0006-caching.md) | Caching strategy (result + LLM) |
| [ADR-0007](docs/ADR-0007-guardrails-dos-capas.md) | Two-layer guardrails with retry cap |
| [ADR-0008](docs/ADR-0008-salida-estructurada-pydantic.md) | Structured output with Pydantic |
| [ADR-0009](docs/ADR-0009-versionado-prompts-eval-gate.md) | Prompt versioning + CI eval gate |
| [ADR-0010](docs/ADR-0010-agent-as-judge.md) | Agent-as-Judge with a different model |
| [ADR-0011](docs/ADR-0011-human-in-the-loop-interrupt.md) | Human-in-the-loop with `interrupt()` |
| [ADR-0012](docs/ADR-0012-patron-tools.md) | Tools pattern: gather with LLM, act deterministically |
| [ADR-0013](docs/ADR-0013-memoria-episodica.md) | Episodic memory only (no conversational) |
| [ADR-0014](docs/ADR-0014-multimodal-vision.md) | Multimodal extraction with Claude Vision |
