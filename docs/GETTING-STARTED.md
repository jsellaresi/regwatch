# Getting Started — RegWatch

Practical guide to **set up and use** RegWatch. For the architectural *why* behind each decision, see the [ADR index](README.md). For exhaustive testing paths, see [RUNBOOK.md](../../RUNBOOK.md).

---

## The core concept (read this first)

RegWatch works with **two completely different types of PDF**. Confusing them is the #1 source of confusion:

| | Regulatory corpus | Company policy |
|---|---|---|
| **What it is** | The laws: GDPR, MiFID II, 4AMLD, 5AMLD, 6AMLD | Your internal policy document (data retention, KYC, etc.) |
| **Where it lives** | Stored permanently in pgvector | Uploaded on demand via the UI |
| **When to load it** | Once at setup, again only if regulations change | Every time you want to analyze a policy |
| **How to load it** | "Ingestar regulaciones" button in the UI (or CLI) | Upload field in the UI |

```
Your company policy PDF  ──► RegWatch pipeline ──► Gap report
                                      │
              GDPR / MiFID II / AML ◄─┘   (already in the vector store)
```

---

## 1. Prerequisites

- **Docker** and **Docker Compose v2** installed
- API keys — copy `.env.example` to `.env` and fill in:

```bash
cp .env.example .env
```

| Key | Required | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | Analysis LLM (Claude) + Vision for scanned PDFs |
| `OPENAI_API_KEY` | ✅ | Embeddings (`text-embedding-3-small`) + Judge (GPT-4o) |
| `LANGFUSE_PUBLIC_KEY` | ✅ | Observability traces |
| `LANGFUSE_SECRET_KEY` | ✅ | Observability traces |
| `LANGFUSE_HOST` | ✅ | e.g. `https://cloud.langfuse.com` |
| `JIRA_API_TOKEN` | ❌ | Ticket creation (errors gracefully if absent) |
| `COHERE_API_KEY` | ❌ | Cloud reranking (falls back to local model if absent) |

---

## 2. Start the stack

```bash
cd regwatch
docker compose up -d --build
```

Three services start:

| Service | URL | Purpose |
|---|---|---|
| Frontend | http://localhost:5173 | The UI you interact with |
| API | http://localhost:8000/docs | FastAPI + Swagger |
| PostgreSQL | localhost:5432 | Vector store + checkpoints + cache |

---

## 3. Load the regulatory corpus (once)

This step loads the regulation PDFs (`data/`) into the vector store. It only needs to be done **once** — the data persists across container restarts in the `pgdata` Docker volume.

**Option A — via the UI (recommended):**

Open http://localhost:5173, find the **"BASE DE REGULACIONES"** card, and click **"Ingestar regulaciones"**. A progress bar shows each regulation loading in real time.

**Option B — via CLI:**

```bash
docker compose exec api python -m scripts.ingest_regulations
```

**Verify it worked:**

```bash
docker compose exec db psql -U regwatch -d regwatch -c "SELECT count(*) AS chunks FROM langchain_pg_embedding;"
# Should return > 2000 chunks
```

**Optional — create the HNSW vector index for faster search:**

```bash
docker compose exec db psql -U regwatch -d regwatch -c "CREATE INDEX IF NOT EXISTS idx_emb_hnsw ON langchain_pg_embedding USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64);"
```

> You only need to re-run the ingestion if a regulation is amended or you add new regulations to `data/`.

---

## 4. Register the analysis prompt (once)

```bash
docker compose exec api python -m scripts.register_prompts
```

This creates the versioned prompt in LangFuse. Like the corpus, it only needs to be done once (the startup check skips it if already registered).

---

## 5. Analyze a policy

Now the system is ready. To analyze an internal policy document:

1. Open http://localhost:5173
2. Enter a **Policy ID** (any identifier, e.g. `gdpr-retention-v1`)
3. **Upload your company's PDF policy document** (not a regulation — your internal document)
4. Click **Analizar**

The pipeline nodes light up in real time as the analysis progresses:

```
Cache → Extraction → Input guardrail → Retrieval → Reranking
     → Tools → Analysis → Output guardrail → Judge → (Human review?) → Report
```

The final report shows:
- **Detected gaps** with regulation references and risk level (HIGH / MEDIUM / LOW)
- **Remediation** suggestion per gap
- **JIRA tickets** (if `JIRA_API_TOKEN` is set)
- **Memory diff** — what was resolved vs. still open vs. new since the last analysis of the same policy

---

## 6. Human review

If the Judge LLM rejects the report after 3 attempts, or the output guardrail fails repeatedly, the pipeline pauses and shows a **"Revisión humana requerida"** alert in the UI.

- Click **Aprobar informe** to continue to the final report
- Click **Rechazar** to re-run the analysis

---

## 7. Follow-up chat

After a report is generated, a chat panel appears. Ask questions about the report:

> *"What is the highest-risk gap and why?"*
> *"Which gaps relate to data retention?"*

The chat has context from the full report generated in that session.

---

## 8. Stopping and restarting

```bash
docker compose down          # stops containers, data survives in pgdata volume
docker compose down -v       # stops + deletes all data (requires re-ingestion)
docker compose up -d         # restart without rebuilding
docker compose up -d --build # restart and rebuild images (after code changes)
```

> After `docker compose up -d` (no `--build`), the regulatory corpus and registered prompt are **already there** — no need to re-ingest or re-register.
