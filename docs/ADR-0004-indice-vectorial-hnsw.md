# ADR-0004: Índice vectorial HNSW e índices de base de datos

- **Estado:** Aceptada
- **Fecha:** 2026-06-25

## Contexto

La búsqueda semántica sobre pgvector necesita un índice de aproximación de vecinos más cercanos
(ANN); sin índice, pgvector hace *full scan* (exacto pero O(n) por consulta). pgvector ofrece dos
tipos de índice ANN:

- **IVFFlat:** particiona el espacio en `lists` clústeres; en consulta explora `probes` clústeres.
  Construcción barata, pero **requiere datos representativos al crear el índice** (entrena los
  centroides) y su recall se degrada si el dataset crece o cambia su distribución tras el entreno.
- **HNSW:** grafo jerárquico navegable. Mejor recall y latencia de consulta, construcción más cara y
  mayor uso de memoria; **no requiere entrenamiento previo** y tolera inserciones incrementales.

Además de los embeddings, hay consultas relacionales calientes que también necesitan índice:
lookup de cache por hash y lookup del último episodio por política.

## Decisión

**1. Índice vectorial: HNSW** sobre la columna de embeddings, con distancia coseno:

```sql
CREATE INDEX ON langchain_pg_embedding
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
-- en consulta: SET hnsw.ef_search = 40;
```

- `m = 16`: nº de conexiones por nodo (balance recall/memoria, valor recomendado por defecto).
- `ef_construction = 64`: tamaño de la lista dinámica al construir (mayor = mejor grafo, build más lento).
- `vector_cosine_ops`: coseno, coherente con embeddings normalizados de OpenAI (`text-embedding-3-small`).

**2. Índices relacionales (B-tree):**

```sql
-- lookup de cache por hash del documento (ver ADR-0006)
-- analysis_cache.doc_hash ya es PRIMARY KEY → B-tree implícito
-- último episodio por política (ver ADR-0013)
CREATE INDEX idx_policy ON policy_episodes (policy_id, created_at DESC);
```

El índice compuesto `(policy_id, created_at DESC)` sirve directamente la consulta
"último informe de esta política" (`WHERE policy_id = ? ORDER BY created_at DESC LIMIT 1`) sin sort.

## Consecuencias

**Positivas**
- HNSW da mejor recall/latencia que IVFFlat y, crucialmente, **tolera re-ingestas incrementales**
  del corpus (las regulaciones se enmiendan) sin re-entrenar.
- En compliance el recall importa: un artículo no recuperado = un gap no detectado.
- Los índices B-tree hacen O(log n) los lookups de cache y de memoria.

**Negativas / trade-offs**
- HNSW consume más memoria y su construcción es más lenta que IVFFlat (irrelevante: el corpus son
  miles de chunks, no millones).
- `ef_search` es un parámetro a ajustar: más alto = más recall y más latencia.

## Alternativas consideradas

- **IVFFlat:** descartado por degradación de recall con datos cambiantes y por requerir
  re-entrenamiento de centroides tras re-ingestas.
- **Sin índice (full scan exacto):** descartado; O(n) por consulta no escala aunque sea exacto.
- **Distancia L2/inner product:** descartada frente a coseno por coherencia con embeddings normalizados.

## Referencias

- `use_case_regwatch.md` → "Phase 3 — RAG", `migrations/002_memory.sql`, "Phase 1 — Caching".
- Curso: Block 10 (pgvector, IVFFlat vs HNSW, operadores de similitud, schema design).
