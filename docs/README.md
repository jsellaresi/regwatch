# Architecture Decision Records — RegWatch

Este directorio registra las **decisiones de arquitectura** (ADRs) del sistema RegWatch, la
plataforma de análisis de compliance descrita en [`../../use_case_regwatch.md`](../../use_case_regwatch.md).

Cada ADR documenta el *por qué* de una decisión: el contexto, la opción elegida, sus consecuencias
y las alternativas descartadas. Formato basado en [MADR](https://adr.github.io/madr/).

## Índice

| #    | Decisión | Estado |
|------|----------|--------|
| [0001](ADR-0001-langgraph-orquestador.md) | LangGraph (StateGraph) como orquestador central | Aceptada |
| [0002](ADR-0002-postgres-almacen-unificado.md) | PostgreSQL como almacén unificado (pgvector + checkpoints + cache + memoria) | Aceptada |
| [0003](ADR-0003-recuperacion-hibrida.md) | Recuperación híbrida: pgvector + BM25 con Reciprocal Rank Fusion | Aceptada |
| [0004](ADR-0004-indice-vectorial-hnsw.md) | Índice vectorial HNSW e índices de base de datos | Aceptada |
| [0005](ADR-0005-reranking-cross-encoder.md) | Reranking con cross-encoder | Aceptada |
| [0006](ADR-0006-caching.md) | Estrategia de caching (resultado + LLM) | Aceptada |
| [0007](ADR-0007-guardrails-dos-capas.md) | Guardrails de dos capas con tope de reintentos | Aceptada |
| [0008](ADR-0008-salida-estructurada-pydantic.md) | Salida estructurada con Pydantic | Aceptada |
| [0009](ADR-0009-versionado-prompts-eval-gate.md) | Versionado de prompts + eval gate en CI | Aceptada |
| [0010](ADR-0010-agent-as-judge.md) | Agent-as-Judge con modelo distinto | Aceptada |
| [0011](ADR-0011-human-in-the-loop-interrupt.md) | Human-in-the-loop con `interrupt()` | Aceptada |
| [0012](ADR-0012-patron-tools.md) | Patrón de tools: recopilar con LLM vs actuar determinista | Aceptada |
| [0013](ADR-0013-memoria-episodica.md) | Memoria episódica únicamente (no conversacional) | Aceptada |
| [0014](ADR-0014-multimodal-vision.md) | Extracción multimodal con Claude Vision | Aceptada |

## Convenciones

- **Estados posibles:** Propuesta · Aceptada · Rechazada · Reemplazada por ADR-NNNN.
- Las ADRs son **inmutables**: si una decisión cambia, se crea una nueva ADR que reemplaza a la anterior.
- Numeración secuencial de cuatro dígitos. La fecha es la de aceptación.
