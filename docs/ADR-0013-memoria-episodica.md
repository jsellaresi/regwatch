# ADR-0013: Memoria episódica únicamente (no conversacional completa)

- **Estado:** Aceptada
- **Fecha:** 2026-06-25

## Contexto

"Añadir memoria" a un sistema LLM puede significar varias cosas (Block 5 y Block 10): buffer
conversacional completo, resumen comprimido, o memoria episódica/largo plazo. El pipeline core de
RegWatch es un análisis **single-shot** de un documento: no hay una conversación que recordar entre
turnos. Meter un buffer conversacional completo en el estado del grafo lo inflaría sin aportar valor.

Sin embargo, hay una necesidad real de compliance que **sí** requiere memoria: cuando se reenvía una
**versión corregida** de una política, el oficial quiere saber qué gaps se resolvieron, cuáles siguen
abiertos y cuáles son nuevos (*regression tracking*).

## Decisión

Implementar **solo memoria episódica de largo plazo**, no conversacional:

- Tabla `policy_episodes` (Postgres): cada informe aprobado se guarda por `policy_id`.
- `diff_with_memory` (dentro de `format_report`) compara el informe actual con el último episodio de
  esa política y etiqueta cada gap como **resuelto / sigue abierto / nuevo**.
- `store_episodic_memory` es el penúltimo nodo: persiste el informe aprobado como nuevo episodio.

Para el **chat de seguimiento** de la UI (Phase 11) se usa un **buffer de sesión** ligero, pero vive
en la API (`SESSION_BUFFER`), **no** en el estado del grafo, para no contaminar el pipeline core.

## Consecuencias

**Positivas**
- Aporta *regression tracking* entre reenvíos, una necesidad real de compliance, reutilizando la
  infraestructura Postgres/pgvector existente ([ADR-0002](ADR-0002-postgres-almacen-unificado.md)).
- El estado del grafo permanece acotado (sin historiales conversacionales).
- Separación clara: memoria de negocio (episódica, en el grafo) vs. UX de chat (sesión, en la API).

**Negativas / trade-offs**
- La identidad de un gap se aproxima con `regulation_ref + descripción` truncada; cambios grandes de
  redacción del mismo gap podrían contarse como "nuevo". Suficiente para el caso; afinable.
- Requiere un `policy_id` estable como clave de la política (lo aporta el cliente al subir).

## Alternativas consideradas

- **Buffer conversacional completo en el grafo:** descartado; innecesario para un flujo single-shot e
  infla el estado.
- **Resumen comprimido (summary memory):** descartado; el documento ya es la fuente, sería redundante.
- **Sin memoria:** descartado; se perdería el *regression tracking* entre versiones de una política.

## Referencias

- `use_case_regwatch.md` → "Phase 8 — Memory" (tabla de veredicto), `graph/nodes/memory.py`,
  `migrations/002_memory.sql`, "Phase 11" (buffer de sesión).
- Curso: Block 5 (tipos de memoria), Block 10 (memoria episódica en PostgreSQL).
