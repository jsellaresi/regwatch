# ADR-0002: PostgreSQL como almacén unificado

- **Estado:** Aceptada
- **Fecha:** 2026-06-25

## Contexto

RegWatch necesita persistir cuatro tipos de datos muy distintos:

1. **Embeddings** del corpus regulatorio para RAG (búsqueda vectorial).
2. **Checkpoints** del grafo LangGraph (para HITL y recuperación).
3. **Cache** de resultados de análisis y de llamadas LLM.
4. **Memoria episódica** (histórico de informes por política).

Una opción es usar una pieza especializada por necesidad: una vector DB dedicada (Pinecone,
Weaviate), Redis para cache, otra store para checkpoints. Eso multiplica la infraestructura, los
puntos de fallo y el coste operativo de un equipo de tamaño medio.

## Decisión

Usar **PostgreSQL como almacén único** para las cuatro necesidades:

- **pgvector** para embeddings y búsqueda por similitud (ver [ADR-0004](ADR-0004-indice-vectorial-hnsw.md)).
- **`PostgresSaver`** de LangGraph para checkpoints.
- Tablas `analysis_cache` (cache de resultados) + `SQLAlchemyCache` (cache de LLM).
- Tabla `policy_episodes` para memoria episódica.

## Consecuencias

**Positivas**
- Un solo motor que operar, respaldar y monitorizar; menos lock-in que una vector DB propietaria.
- Transaccionalidad y joins entre datos relacionales y vectoriales cuando hace falta.
- pgvector es suficiente en precisión/latencia para el tamaño de este corpus (ver ADR-0004).
- Coste predecible; despliegue trivial en RDS/Cloud SQL (Block 16).

**Negativas / trade-offs**
- Postgres no iguala a una vector DB dedicada en colecciones de cientos de millones de vectores
  (no es el caso aquí: el corpus regulatorio son miles de chunks).
- Cache en Postgres tiene más latencia que Redis en memoria; aceptable porque el cache de resultado
  evita un pipeline de ~12 s y el de LLM solo deduplica reintentos.

## Alternativas consideradas

- **Vector DB dedicada (Pinecone/Weaviate) + Redis + store de checkpoints:** descartada por
  sobre-ingeniería para el volumen y por multiplicar infraestructura.
- **Solo en memoria / ficheros:** descartada; no sobrevive a reinicios ni soporta HITL persistente.

## Referencias

- Código: `migrations/001_cache.sql`, `002_memory.sql`.
- Curso: Block 10 (PostgreSQL + pgvector, unified stack).
