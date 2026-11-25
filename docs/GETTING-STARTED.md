# Getting started — RegWatch

Practical guide to **configuring and using** RegWatch. For the *why* behind each architectural decision, see the [ADR index](README.md). For exhaustive test paths, see the [RUNBOOK.md](RUNBOOK.md).

---

## The core concept (read this first)

RegWatch works with **two completely different types of PDF**. Confusing them is the number 1 source of confusion:

| | Regulatory corpus | Company policy |
|---|---|---|
| **What it is** | The laws: GDPR, MiFID II, 4AMLD, 5AMLD, 6AMLD | Your internal policy document (data retention, KYC, etc.) |
| **Where it lives** | Stored permanently in pgvector | Uploaded on demand from the UI |
| **When to load it** | Once, at setup, only if the regulations change | Every time you want to analyze a policy |
| **How to load it** | "Ingestar regulaciones" button in the UI (or CLI) | File upload field in the UI |

```
Your internal policy PDF  ──► RegWatch pipeline ──► Gap report
                                           │
              GDPR / MiFID II / AML ◄──────┘   (already in the vector store)
```

---

## 1. Prerequisites

- **Docker** and **Docker Compose v2** installed
- API keys — copy `.env.example` to `.env` and fill in the values:

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
| `JIRA_API_TOKEN` | ❌ | JIRA authentication token (required if `JIRA_ENABLED=true`) |
| `JIRA_ENABLED` | ❌ | Set to `true` to create JIRA tickets (default `false`) |
| `JIRA_BASE_URL` | ❌ | Base URL of your Atlassian instance (e.g. `https://acme.atlassian.net`) |
| `COHERE_API_KEY` | ❌ | Cloud reranking (uses a local model if not set) |

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

**Option A — from the UI (recommended):**

Open http://localhost:5173, find the **"BASE DE REGULACIONES"** card (REGULATIONS BASE) and click **"Ingestar regulaciones"** (Ingest regulations). A progress bar shows in real time how each regulation is loaded.

**Option B — from the CLI:**

```bash
docker compose exec api python -m scripts.ingest_regulations
```

**Verify it worked:**

```bash
docker compose exec db psql -U regwatch -d regwatch -c "SELECT count(*) AS chunks FROM langchain_pg_embedding;"
# Should return > 2000 chunks
```

**Optional — create the HNSW vector index for faster searches:**

```bash
docker compose exec db psql -U regwatch -d regwatch -c "CREATE INDEX IF NOT EXISTS idx_emb_hnsw ON langchain_pg_embedding USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64);"
```

> You only need to re-run ingestion if a regulation is modified or you add new regulations to `data/`.

---

## 4. Register the analysis prompt (once)

```bash
docker compose exec api python -m scripts.register_prompts
```

This creates the versioned prompt in LangFuse. Like the corpus, it only needs to be done once (the startup check skips it if it is already registered).

---

## 5. Run the evals (quality gate)

Before analyzing real policies, verify that the registered prompt passes the quality thresholds. The evals measure precision and recall against a golden dataset and validate that citations have the correct format.

**Requirement:** the local environment must be set up with `uv sync` (see the previous section) and the Docker DB must be running.

```bash
uv run pytest evals/eval_suite.py -v
```

Thresholds that must be met (if they fail, the build is considered broken):

| Test | Threshold |
|---|---|
| `test_average_precision_above_threshold` | average precision ≥ 0.85 |
| `test_average_recall_above_threshold` | average recall ≥ 0.80 |
| `test_no_hallucinated_citations` | 0 citations with incorrect format |

If all three tests pass green, the prompt in `staging` is valid for production. Promote it:

```bash
uv run python -m scripts.promote_prompt --from staging --to production
```

> Detailed per-case results (inputs, outputs, metrics) can be viewed in the **LangFuse** dashboard (`LANGFUSE_HOST` from `.env`) under the configured project.

---

## 6. Analyze a policy

The system is now ready. To analyze an internal policy document:

1. Open http://localhost:5173
2. Enter a **policy ID** (any identifier, e.g. `gdpr-retencion-v1`)
3. **Upload your company's policy PDF** (not a regulation — your internal document)
4. Click **Analizar** (Analyze)

The pipeline nodes light up in real time as the analysis progresses:

```
Caché → Extracción → Guardrail entrada → Recuperación → Reranking
     → Herramientas → Análisis → Guardrail salida → Juez → (¿Revisión humana?) → Informe
```

UI labels, in order: Caché (Cache), Extracción (Extraction), Guardrail entrada (Input guardrail), Recuperación
(Retrieval), Reranking, Herramientas (Tools), Análisis (Analysis), Guardrail salida (Output guardrail), Juez (Judge),
¿Revisión humana? (Human review?), Informe (Report).

The final report shows:
- **Detected gaps** with regulatory references and risk level (ALTO / MEDIO / BAJO = HIGH / MEDIUM / LOW)
- **Remediation** suggested per gap
- **JIRA tickets** (if `JIRA_API_TOKEN` is configured)
- **Memory diff** — what was resolved vs. still open vs. new since the last analysis of the same policy

---

## 7. Human review

If the LLM judge rejects the report after 3 attempts, or the output guardrail fails repeatedly, the pipeline pauses and
shows an alert **"Revisión humana requerida"** ("Human review required") in the UI.

- Click **Aprobar informe** (Approve report) to continue to the final report
- Click **Rechazar** (Reject) to re-run the analysis

---

## 8. Follow-up chat

After a report is generated, a chat panel appears. Ask questions about the report:

> *"¿Cuál es la brecha de mayor riesgo y por qué?"* (What is the highest-risk gap and why?)
> *"¿Qué brechas están relacionadas con la retención de datos?"* (Which gaps are related to data retention?)

The chat has context from the full report generated in that session.

---

## 9. Stopping and restarting

```bash
docker compose down          # stops the containers; data survives in the pgdata volume
docker compose down -v       # stops and deletes all data (requires re-ingesting)
docker compose up -d         # restarts without rebuilding
docker compose up -d --build # restarts and rebuilds the images (after code changes)
```

> After `docker compose up -d` (without `--build`), the regulatory corpus and the registered prompt **are already there** — no need to re-ingest or re-register.
