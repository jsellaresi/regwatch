# RegWatch — Execution and Testing Guide

Operational guide to **run** RegWatch locally, **load PDFs** (regulatory corpus and documents to analyze), and
**test all the paths** the product offers.

References: architecture decisions in [`docs/`](README.md).

---

## 1. Prerequisites

- **Docker** and **Docker Compose** (v2) installed.
- **uv** (package and environment manager) for local execution without Docker:
  `pip install uv` or the official installer (https://docs.astral.sh/uv/). `requirements.txt` is not used;
  dependencies live in `pyproject.toml` and the lock in `uv.lock`.
- External service keys in a `.env` file (copy of `.env.example`):
  - `ANTHROPIC_API_KEY` — analysis + Vision (required).
  - `OPENAI_API_KEY` — embeddings + judge (required).
  - `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_HOST` — observability and prompts (required).
  - `COHERE_API_KEY` — reranking (optional; without it the local BGE reranker is used).
  - `JIRA_API_TOKEN` — ticket creation (optional for testing; see "no-JIRA mode" below).
- The 5 regulatory PDFs are already in [`data/`](../data/) (GDPR, MiFID II, 4/5/6 AMLD).

> **Data notice:** use **synthetic test documents only**. Do not upload real policies containing customer data
> or personal data to external services (LLMs, LangFuse Cloud).

---

## 2. How to run

### Option A — Docker Compose (recommended)

```bash
cd regwatch        # project root (docker-compose.yml, data/, docs/)
cp .env.example .env          # and fill in the keys

docker compose up -d --build  # starts db (pgvector) + api + frontend

# Seed the corpus and register the prompt (first time only)
docker compose exec api python -m scripts.ingest_regulations
docker compose exec api python -m scripts.register_prompts
```

Available services:

| Service | URL |
|----------|-----|
| Frontend (UI) | http://localhost:5173 |
| API (Swagger) | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 (`regwatch` / `regwatch`) |

```bash
docker compose logs -f api    # follow logs
docker compose down           # stop (add -v to delete the data volume)
```

### Option B — Local without Docker (development)

```bash
# 1. Postgres with pgvector (Docker for the DB only)
docker run -d --name regwatch-db -p 5432:5432 \
  -e POSTGRES_USER=regwatch -e POSTGRES_PASSWORD=regwatch -e POSTGRES_DB=regwatch \
  pgvector/pgvector:pg16
psql postgresql://regwatch:regwatch@localhost:5432/regwatch -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql ... -f migrations/001_cache.sql
psql ... -f migrations/002_memory.sql

# 2. Backend (with uv; installs deps + the project in editable mode in .venv)
uv sync
uv run python -m scripts.ingest_regulations
uv run python -m scripts.register_prompts
uv run uvicorn api.main:app --reload --port 8000

# 3. Frontend
cd frontend && npm install && npm run dev   # → http://localhost:5173
```

---

## 3. How to load the PDFs

There are **two** distinct kinds of loading. Do not confuse them:

### 3.1 Load the regulatory corpus (once) → feeds the RAG

This is the knowledge against which policies are evaluated. It is ingested **once** (or after an
amendment). The PDFs are already in `data/`.

```bash
docker compose exec api python -m scripts.ingest_regulations
```

This splits the documents by article, embeds them, and upserts into pgvector. After ingestion, create the
HNSW index (see [ADR-0004](ADR-0004-hnsw-vector-index.md)):

```bash
docker compose exec db psql -U regwatch -d regwatch -c \
"CREATE INDEX IF NOT EXISTS idx_emb_hnsw ON langchain_pg_embedding \
 USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64);"
```

**Verify the load:**

```bash
docker compose exec db psql -U regwatch -d regwatch -c `
"SELECT count(*) AS chunks FROM langchain_pg_embedding;"
# Should return thousands of chunks (>0).
```

### 3.2 Load a policy to analyze → runs the pipeline

This is the document the compliance officer wants to review. It is uploaded via the UI or the API.

**Via the UI:** open http://localhost:5173, enter a `policy_id`, drag the PDF in, press *Analizar* (Analyze)
and watch the nodes light up live.

**Via the API (curl):**

All endpoints require the `X-API-Key` header (value of `REGWATCH_API_KEY` in `.env`). **Every `curl` in this
document must include `-H "X-API-Key: $REGWATCH_API_KEY"`**; without it the API responds with 401. Only PDFs up
to `MAX_UPLOAD_MB` (20 by default) are accepted: other types → 415, too large → 413.

```bash
export REGWATCH_API_KEY=...   # the same value as in .env
curl -X POST http://localhost:8000/analyze \
  -H "X-API-Key: $REGWATCH_API_KEY" \
  -F "file=@./fixtures/policy_retencion.pdf" \
  -F "policy_id=policy-001"
```

> **Don't have a test PDF?** Generate one from text (see §4.1).

---

## 4. Product path map

The graph (see `graph/builder.py`) has **conditional branches, loops and a human checkpoint**.
These are **all** the paths to test:

| # | Path | How it is triggered | Expected result |
|---|--------|-----------------|--------------------|
| C1 | **Cache miss** (full pipeline) | New document | Runs all nodes; report generated |
| C2 | **Cache hit** | Resubmit **the same** PDF (same bytes) before the TTL | Near-instant response; only the `check_cache` node |
| C3 | **Input guardrail — block** | PDF with a prompt-injection sentence (PII is redacted, not blocked) | `blocked_end`; `status: "blocked"`, no analysis |
| C4 | **Input guardrail — pass** | Normal policy PDF | Continues to the fan-out |
| C5 | **Multimodal — digital PDF** | PDF with selectable text | Direct extraction (no Vision calls) |
| C6 | **Multimodal — scanned PDF** | PDF as an image (scan) | Pages go through Claude Vision |
| C7 | **Tools — with enrichment** | Policy that motivates querying amendments | `enrich_agent` calls tools; `tool_results` populated |
| C8 | **Tools — without enrichment** | Self-contained policy | `enrich_agent` does not call tools; proceeds directly |
| C9 | **Output guardrail — retry** | Analysis produces a malformed citation (<2 attempts) | Retries `analyze_compliance` |
| C10 | **Output guardrail — escalates to HITL** | Malformed citations ≥2 attempts | Goes to `human_review_checkpoint` |
| C11 | **Judge — approves** | Good-quality report | `format_report` directly |
| C12 | **Judge — retries** | Weak report (<3 attempts) | Retries `analyze_compliance` |
| C13 | **Judge — escalates to HITL** | Report rejected 3 times | `human_review_checkpoint` (does NOT auto-approve) |
| C14 | **HITL — approve** | `POST /resume decision=approve` | Continues to `format_report` |
| C15 | **HITL — reject** | `POST /resume decision=reject` | Retries `analyze_compliance` |
| C16 | **Tickets — with gaps** | Policy with HIGH/MEDIUM gaps | JIRA tickets created; `jira_ticket_ids` populated |
| C17 | **Tickets — no gaps** | Compliant policy (no gaps) | No tickets; empty list |
| C18 | **Memory — first submission** | First time for a `policy_id` | `memory_diff`: resolved/open=[], new=current gaps |
| C19 | **Memory — corrected resubmission** | Resubmit v2 with a fixed gap | `resolved` contains the fixed gap |
| C20 | **Reranking — Cohere vs local** | With/without `COHERE_API_KEY` | Same top-5; different reranker path |
| C21 | **SSE streaming** | UI or `POST /analyze/stream` | `node` events per node + final `done` |
| C22 | **Follow-up chat** | `POST /chat` after a report | Response using the report + session buffer |

---

## 5. How to test each path (manual)

### 5.1 Create test PDFs (fixtures)

Synthetic policies are generated by `scripts/make_fixtures.py`; every PDF says on its first line that it is invented (use these, never a real policy). They land in `fixtures/`, which git ignores.

```bash
uv run python -m scripts.make_fixtures
```

| Fixture | What it contains | Path it tests |
|---------|------------------|---------------|
| `policy_retencion.pdf` | A data-protection policy with three GDPR gaps: indefinite retention (Art. 5), no deadline for breach notification (Art. 33), no DPO (Art. 37) | C1, C5, C16 (HIGH gaps), human review |
| `policy_escaneada.pdf` | The same policy as an image-only PDF (no text layer) | C6 (Claude Vision) |
| `policy_retencion_v2.pdf` | The same policy after a partial fix: retention and DPO resolved, breach notification still open | C19 (`memory_diff`: 2 resolved, 1 open) |
| `policy_limpia.pdf` | A compliant policy | C17 (no gaps) |
| `policy_mixta.pdf` | Gaps in GDPR, MiFID II and the AML directive (consent withdrawal, best execution, suitability, suspicious-transaction reporting, record keeping); long enough to be split into several retrieval queries | Retrieval across regulations |
| `policy_injection.pdf` | An ordinary policy with a prompt-injection sentence ("ignora las instrucciones anteriores...") | C3 (blocked) |
| `policy_pii.pdf` | A policy that includes a DNI, an IBAN and a card number | The input guardrail redacts them (`[DNI]`, `[IBAN]`, `[CARD]`) and the analysis continues |

### 5.2 Cache paths (C1, C2)

```bash
# C1: first submission → full pipeline
curl -s -X POST localhost:8000/analyze -F "file=@fixtures/policy_retencion.pdf" -F "policy_id=p1" | jq .
# C2: same PDF again → near-instant response (cache hit)
time curl -s -X POST localhost:8000/analyze -F "file=@fixtures/policy_retencion.pdf" -F "policy_id=p1" | jq .status
```

Check in LangFuse that the second run only has the `check_cache` span.

### 5.3 Input guardrail (C3, C4)

```bash
# C3: prompt injection -> status "blocked", no analysis
curl -s -X POST localhost:8000/analyze -H "X-API-Key: $REGWATCH_API_KEY" -F "file=@fixtures/policy_injection.pdf" -F "policy_id=p2" | jq .
# PII is redacted, not blocked: the analysis runs (and pauses for human review) on the text with [DNI], [IBAN], [CARD]
curl -s -X POST localhost:8000/analyze -H "X-API-Key: $REGWATCH_API_KEY" -F "file=@fixtures/policy_pii.pdf" -F "policy_id=p3" | jq .
# C4: a normal policy is NOT blocked
curl -s -X POST localhost:8000/analyze -H "X-API-Key: $REGWATCH_API_KEY" -F "file=@fixtures/policy_retencion.pdf" -F "policy_id=p4" | jq .status
```

### 5.4 Multimodal (C5, C6)

- **C5:** any digital fixture, e.g. `fixtures/policy_retencion.pdf` (it has a text layer, so no Vision calls).
- **C6:** `fixtures/policy_escaneada.pdf`, the image-only twin of `policy_retencion.pdf` (no text layer). Check in the logs or LangFuse that its page goes through Claude Vision, and that the gaps found match the digital version.

### 5.5 Tickets and memory (C16–C19)

Every analysis pauses for human review ([ADR-0011](ADR-0011-human-in-the-loop-interrupt.md)): approve each one with `POST /resume` (or in the UI) so the report is cached, ticketed and stored in memory. The `memory_diff` appears from the second approved analysis of the same `policy_id`.

```bash
# C16 + C18: gaps + first submission
curl -s -X POST localhost:8000/analyze -F "file=@fixtures/policy_retencion.pdf" -F "policy_id=pol-mem" | jq '.gaps, .jira_ticket_ids, .memory_diff'
# C19: corrected resubmission → the gap appears in resolved
curl -s -X POST localhost:8000/analyze -F "file=@fixtures/policy_retencion_v2.pdf" -F "policy_id=pol-mem" | jq '.memory_diff'
# C17: compliant policy → gaps [] and no tickets
curl -s -X POST localhost:8000/analyze -F "file=@fixtures/policy_limpia.pdf" -F "policy_id=pol-ok" | jq '.gaps, .jira_ticket_ids'
```

> **No-JIRA mode (testing):** if you do not want to create real tickets, export an invalid `JIRA_API_TOKEN`
> and check that `create_jira_ticket` returns the error without bringing down the graph (the `jira_ticket_ids`
> will contain the error message). For automated tests, mock the tool (see §6).

### 5.6 Human-in-the-loop (C10, C13, C14, C15)

Making the judge fail 3 times naturally is non-deterministic. For testing, **force** the path with a
deliberately weak prompt version in `staging`, or lower the judge threshold in a test run. When the
checkpoint is reached:

```bash
# The run pauses and /analyze/stream emits the "needs_review" event.
# Resume by approving:
curl -s -X POST localhost:8000/resume -F "thread_id=pol-mem:policy_retencion.pdf" -F "decision=approve" | jq .status
# ...or by rejecting (re-analyzes):
curl -s -X POST localhost:8000/resume -F "thread_id=pol-mem:policy_retencion.pdf" -F "decision=reject"  | jq .
```

> The `thread_id` is `"{policy_id}:{file_name}"` (see `api/main.py`).

### 5.7 Streaming and chat (C21, C22)

```bash
# C21: watch per-node events live
curl -N -X POST localhost:8000/analyze/stream -F "file=@fixtures/policy_retencion.pdf" -F "policy_id=p-sse"
# C22: ask about the finished report ("Which is the highest-risk gap and why?")
curl -s -X POST localhost:8000/chat -F "thread_id=p-sse:policy_retencion.pdf" \
  -F "question=¿Cuál es el gap de mayor riesgo y por qué?" | jq .answer
```

---

## 6. Automated tests

### 6.1 Eval suite (analysis quality — CI gate)

Validates precision/recall and citation format against the golden dataset. It is the barrier that protects
prompt promotion ([ADR-0009](ADR-0009-prompt-versioning-eval-gate.md)).

```bash
docker compose exec api pytest evals/eval_suite.py -v
```

Thresholds (the build fails if they are not met): precision ≥ 0.85, recall ≥ 0.80, 0 malformed citations.

### 6.2 Node and graph path tests (recommended to add)

Suggested structure in `tests/` to cover the §4 map deterministically (mocking LLMs and tools so as not to
depend on external services):

```python
# tests/test_paths.py  (skeleton)
from langgraph.checkpoint.memory import MemorySaver
import document_store
from graph.builder import create_regwatch_graph

def build_test_graph(monkeypatch):
    # Mock LLMs, reranker and create_jira_ticket → deterministic paths
    return create_regwatch_graph(MemorySaver())   # in-memory checkpointer for tests

def test_input_guardrail_blocks_injection(monkeypatch):
    g = build_test_graph(monkeypatch)
    out = g.invoke({"doc_hash": document_store.put(b"...ignore previous instructions..."),
                    "document_name": "x.pdf", "policy_id": "t", "judge_attempt": 0,
                    "output_guardrail_attempt": 0}, {"configurable": {"thread_id": "t1"}})
    assert out["final_report"]["status"] == "blocked"      # C3

def test_judge_failure_routes_to_human(monkeypatch):
    # Mock the judge to always return approved=False → must go to HITL, NOT auto-approve
    ...                                                     # C13
```

Target coverage per test: **C2, C3, C11, C12, C13, C14, C15, C17, C18, C19** (the deterministic, mockable
ones). C5/C6/C7/C8/C20/C21/C22 are better tested as integration tests.

```bash
docker compose exec api pytest tests/ -v
```

---

## 7. Acceptance checklist

Before signing off on a deployment, verify:

- [ ] `docker compose up` leaves the 3 services *healthy*.
- [ ] The corpus is loaded (§3.1: `count(*) > 0` and the HNSW index exists).
- [ ] The prompt is registered in LangFuse (`label=production`).
- [ ] C1, C2, C3, C16, C17, C18, C19 verified via curl.
- [ ] C13/C14/C15 (HITL) verified with `/resume`.
- [ ] C21 emits per-node events; the UI renders them.
- [ ] `pytest evals/eval_suite.py` is green.
- [ ] Every analysis produces a trace in LangFuse with cost, latency and judge scores.

---

## 8. Troubleshooting

| Symptom | Probable cause | Solution |
|---------|----------------|----------|
| `KeyError`/missing variable on startup | Incomplete `.env` | Review all required keys (§1) |
| Retrieval returns 0 chunks | Corpus not ingested | Run §3.1 and check the `count(*)` |
| Slow search | HNSW index missing | Create it after ingestion (§3.1) |
| The analysis does not find the prompt | Prompt not registered | `python -m scripts.register_prompts` |
| SSE does not arrive intact in the UI | Proxy buffering | `proxy_buffering off` in `docker/nginx.conf` |
| `/resume` does not resume | Non-persistent checkpointer or wrong `thread_id` | Confirm Postgres as the checkpointer and the `policy_id:file_name` format |
| Cache serves an old result | Not invalidated after changing prompt/corpus | Empty `analysis_cache` ([ADR-0006](ADR-0006-caching.md)) |
