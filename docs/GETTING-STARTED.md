# Primeros pasos — RegWatch

Guía práctica para **configurar y utilizar** RegWatch. Para el *porqué* arquitectónico de cada decisión, consulta el [índice de ADR](README.md). Para rutas de prueba exhaustivas, consulta el [RUNBOOK.md](../../RUNBOOK.md).

---

## El concepto fundamental (léelo primero)

RegWatch trabaja con **dos tipos de PDF completamente distintos**. Confundirlos es la fuente de confusión número 1:

| | Corpus regulatorio | Política de empresa |
|---|---|---|
| **Qué es** | Las leyes: GDPR, MiFID II, 4AMLD, 5AMLD, 6AMLD | Tu documento de política interna (retención de datos, KYC, etc.) |
| **Dónde vive** | Almacenado permanentemente en pgvector | Subido bajo demanda desde la interfaz |
| **Cuándo cargarlo** | Una vez al configurar, solo si cambian las regulaciones | Cada vez que quieras analizar una política |
| **Cómo cargarlo** | Botón "Ingestar regulaciones" en la UI (o CLI) | Campo de subida en la interfaz |

```
Tu PDF de política interna  ──► Pipeline de RegWatch ──► Informe de brechas
                                           │
              GDPR / MiFID II / AML ◄──────┘   (ya en el almacén vectorial)
```

---

## 1. Requisitos previos

- **Docker** y **Docker Compose v2** instalados
- Claves de API — copia `.env.example` a `.env` y rellena los valores:

```bash
cp .env.example .env
```

| Clave | Obligatoria | Propósito |
|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | LLM de análisis (Claude) + Visión para PDFs escaneados |
| `OPENAI_API_KEY` | ✅ | Embeddings (`text-embedding-3-small`) + Juez (GPT-4o) |
| `LANGFUSE_PUBLIC_KEY` | ✅ | Trazas de observabilidad |
| `LANGFUSE_SECRET_KEY` | ✅ | Trazas de observabilidad |
| `LANGFUSE_HOST` | ✅ | p. ej. `https://cloud.langfuse.com` |
| `JIRA_API_TOKEN` | ❌ | Creación de tickets (falla con gracia si no está) |
| `COHERE_API_KEY` | ❌ | Reranking en la nube (usa modelo local si no está) |

---

## 2. Arrancar el stack

```bash
cd regwatch
docker compose up -d --build
```

Se inician tres servicios:

| Servicio | URL | Propósito |
|---|---|---|
| Frontend | http://localhost:5173 | La interfaz con la que interactúas |
| API | http://localhost:8000/docs | FastAPI + Swagger |
| PostgreSQL | localhost:5432 | Almacén vectorial + checkpoints + caché |

---

## 3. Cargar el corpus regulatorio (una vez)

Este paso carga los PDFs de regulaciones (`data/`) en el almacén vectorial. Solo necesita hacerse **una vez** — los datos persisten entre reinicios del contenedor en el volumen Docker `pgdata`.

**Opción A — desde la interfaz (recomendado):**

Abre http://localhost:5173, encuentra la tarjeta **"BASE DE REGULACIONES"** y haz clic en **"Ingestar regulaciones"**. Una barra de progreso muestra en tiempo real cómo se carga cada regulación.

**Opción B — desde la CLI:**

```bash
docker compose exec api python -m scripts.ingest_regulations
```

**Verifica que funcionó:**

```bash
docker compose exec db psql -U regwatch -d regwatch -c "SELECT count(*) AS chunks FROM langchain_pg_embedding;"
# Debería devolver > 2000 chunks
```

**Opcional — crear el índice vectorial HNSW para búsquedas más rápidas:**

```bash
docker compose exec db psql -U regwatch -d regwatch -c "CREATE INDEX IF NOT EXISTS idx_emb_hnsw ON langchain_pg_embedding USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64);"
```

> Solo necesitas volver a ejecutar la ingestión si se modifica una regulación o añades nuevas regulaciones a `data/`.

---

## 4. Registrar el prompt de análisis (una vez)

```bash
docker compose exec api python -m scripts.register_prompts
```

Esto crea el prompt versionado en LangFuse. Al igual que el corpus, solo hace falta hacerlo una vez (la comprobación al arrancar lo omite si ya está registrado).

---

## 5. Ejecutar los evals (gate de calidad)

Antes de analizar políticas reales, verifica que el prompt registrado supera los umbrales de calidad. Los evals miden precisión y recall contra un dataset golden y validan que las citas tengan el formato correcto.

**Requisito:** el entorno local debe estar configurado con `uv sync` (ver sección anterior) y la DB de Docker debe estar levantada.

```bash
uv run pytest evals/eval_suite.py -v
```

Umbrales que deben cumplirse (si fallan, el build se considera roto):

| Test | Umbral |
|---|---|
| `test_average_precision_above_threshold` | precisión media ≥ 0.85 |
| `test_average_recall_above_threshold` | recall medio ≥ 0.80 |
| `test_no_hallucinated_citations` | 0 citas con formato incorrecto |

Si los tres tests pasan en verde, el prompt en `staging` es válido para producción. Promuévelo:

```bash
uv run python -m scripts.promote_prompt --from staging --to production
```

> Los resultados detallados por caso (inputs, outputs, métricas) se pueden consultar en el dashboard de **LangFuse** (`LANGFUSE_HOST` del `.env`) bajo el proyecto configurado.

---

## 6. Analizar una política

Ahora el sistema está listo. Para analizar un documento de política interna:

1. Abre http://localhost:5173
2. Introduce un **ID de política** (cualquier identificador, p. ej. `gdpr-retencion-v1`)
3. **Sube el PDF de política de tu empresa** (no una regulación — tu documento interno)
4. Haz clic en **Analizar**

Los nodos del pipeline se iluminan en tiempo real mientras avanza el análisis:

```
Caché → Extracción → Guardrail entrada → Recuperación → Reranking
     → Herramientas → Análisis → Guardrail salida → Juez → (¿Revisión humana?) → Informe
```

El informe final muestra:
- **Brechas detectadas** con referencias normativas y nivel de riesgo (ALTO / MEDIO / BAJO)
- **Remediación** sugerida por brecha
- **Tickets JIRA** (si `JIRA_API_TOKEN` está configurado)
- **Diff de memoria** — qué se resolvió vs. sigue abierto vs. es nuevo desde el último análisis de la misma política

---

## 7. Revisión humana

Si el LLM juez rechaza el informe tras 3 intentos, o el guardrail de salida falla repetidamente, el pipeline se pausa y muestra una alerta **"Revisión humana requerida"** en la interfaz.

- Haz clic en **Aprobar informe** para continuar al informe final
- Haz clic en **Rechazar** para volver a ejecutar el análisis

---

## 8. Chat de seguimiento

Tras generar un informe, aparece un panel de chat. Haz preguntas sobre el informe:

> *"¿Cuál es la brecha de mayor riesgo y por qué?"*
> *"¿Qué brechas están relacionadas con la retención de datos?"*

El chat tiene contexto del informe completo generado en esa sesión.

---

## 9. Detener y reiniciar

```bash
docker compose down          # detiene los contenedores, los datos sobreviven en el volumen pgdata
docker compose down -v       # detiene y elimina todos los datos (requiere volver a ingestar)
docker compose up -d         # reinicia sin reconstruir
docker compose up -d --build # reinicia y reconstruye las imágenes (tras cambios en el código)
```

> Tras `docker compose up -d` (sin `--build`), el corpus regulatorio y el prompt registrado **ya están ahí** — no es necesario volver a ingestar ni a registrar.
