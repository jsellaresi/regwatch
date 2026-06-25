# ADR-0006: Estrategia de caching (resultado + LLM)

- **Estado:** Aceptada
- **Fecha:** 2026-06-25

## Contexto

Un análisis completo de RegWatch cuesta ~12 s y ~$0.04 (extracción multimodal + retrieval + rerank +
análisis + judge, con posibles reintentos). Dos patrones de gasto son evitables:

1. **El mismo documento se reanaliza** (un oficial reabre el caso, se reenvía idéntico el PDF). Repetir
   todo el pipeline es puro desperdicio.
2. **Llamadas LLM idénticas dentro de un mismo run** (reintentos del análisis, ejecución de la suite
   de evals) recalculan la misma respuesta.

## Decisión

Dos capas de cache complementarias:

1. **Cache de resultado** (`analysis_cache`): primer nodo del grafo (`check_cache`). Clave =
   `sha256(document_bytes)`. Si existe un informe **vigente** (TTL = 7 días) se hace *short-circuit*
   y se devuelve sin ejecutar nada más. `write_cache` lo persiste tras `format_report`.
2. **Cache de LLM** (`set_llm_cache(SQLAlchemyCache(...))`): deduplica llamadas idénticas al modelo
   durante reintentos y evals.

**Invalidación** (clave para corrección en compliance): vaciar/expirar el cache de resultado cuando
(a) se promociona una nueva versión de prompt ([ADR-0009](ADR-0009-versionado-prompts-eval-gate.md)),
o (b) se re-ingesta una regulación — un informe antiguo podría basarse en texto regulatorio obsoleto.
El TTL de 7 días es un segundo seguro por si falla la invalidación explícita.

## Consecuencias

**Positivas**
- Documentos repetidos: respuesta casi instantánea y coste ~0.
- El cache de LLM abarata reintentos y evals sin lógica adicional en los nodos.
- Hash por bytes: si el PDF cambia un solo byte, la clave cambia y no se sirve un resultado obsoleto.

**Negativas / trade-offs**
- Riesgo de servir un informe desactualizado si se olvida invalidar; mitigado por TTL + invalidación
  en los dos eventos que cambian la semántica (prompt y corpus).
- Cache en Postgres añade algo de latencia frente a Redis; aceptable dado lo que ahorra.

## Alternativas consideradas

- **Sin cache:** descartado; coste y latencia innecesarios en reanálisis.
- **Cache en Redis:** válido pero añade infraestructura; se prefiere Postgres por unificación
  ([ADR-0002](ADR-0002-postgres-almacen-unificado.md)). Migrable si el volumen lo exige.
- **Clave por nombre de fichero o `policy_id`:** descartada; dos PDFs distintos podrían colisionar o
  un mismo nombre cambiar de contenido. El hash de bytes es la identidad correcta.

## Referencias

- `use_case_regwatch.md` → "Phase 1 — Caching y Control de Coste", `graph/nodes/cache.py`,
  `config.py` (set_llm_cache), `migrations/001_cache.sql`.
- Curso: Block 10 (response cache con TTL).
