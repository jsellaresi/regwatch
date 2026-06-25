# ADR-0011: Human-in-the-loop con `interrupt()`

- **Estado:** Aceptada
- **Fecha:** 2026-06-25

## Contexto

El juez ([ADR-0010](ADR-0010-agent-as-judge.md)) puede rechazar un informe repetidamente. La versión
inicial del diseño resolvía esto con `judge_passed = approved or attempt >= 3`: es decir, tras 3
intentos **auto-aprobaba** un informe que el evaluador había rechazado tres veces. En un sistema de
compliance esto es inaceptable: se emitiría un informe de baja calidad y se abrirían tickets JIRA
sobre conclusiones no fiables, sin que ningún humano lo supiera.

Se necesita que, cuando la automatización no alcanza la calidad mínima, **una persona decida** — y
que el sistema pueda **pausar** esperando esa decisión, potencialmente durante minutos u horas, sin
mantener un proceso bloqueado en memoria.

## Decisión

Sustituir el force-pass por un nodo `human_review_checkpoint` que usa **`interrupt()`** de LangGraph:

- Cuando el juez agota los reintentos (o el guardrail de salida agota los suyos), el grafo enruta a
  `human_review_checkpoint`, que llama a `interrupt({...})` con el informe y los scores.
- `interrupt()` **detiene el grafo y persiste su estado** vía el checkpointer Postgres
  ([ADR-0002](ADR-0002-postgres-almacen-unificado.md)). El proceso no queda bloqueado: el run termina
  y puede reanudarse después.
- El oficial revisa (en la UI, Phase 11) y la API reanuda con
  `graph.invoke(Command(resume="approve"|"reject"), config)` sobre el mismo `thread_id`.
- `approve` → `format_report`; `reject` → reintenta el análisis.

## Por qué `interrupt()` y no otras formas de "pausa"

- **No** se puede usar un simple `input()` o bloquear el hilo: la pausa puede durar horas y debe
  sobrevivir a reinicios del servidor.
- `interrupt()` + checkpointer materializa el estado en Postgres, así que la reanudación es
  *stateless* desde el punto de vista del proceso: cualquier worker puede retomar el `thread_id`.
- Es la primitiva nativa de LangGraph para HITL; reinventarla con colas/flags sería más frágil.

## Consecuencias

**Positivas**
- Ningún informe rechazado por el juez se emite automáticamente; siempre lo valida un humano.
- La pausa es duradera y resistente a reinicios (estado en Postgres), no un hilo en espera.
- Reanudación distribuible por `thread_id`; encaja con el streaming SSE de la UI.

**Negativas / trade-offs**
- Requiere checkpointer persistente configurado (ya es requisito por ADR-0002).
- La UI/API debe gestionar el estado "pendiente de revisión" y exponer approve/reject.

## Alternativas consideradas

- **Force-pass tras N intentos:** descartado; auto-aprueba informes no fiables (el bug original).
- **Fallar y abortar el run:** descartado; pierde el trabajo ya hecho y no permite intervención.
- **Cola externa + flag manual:** descartado; reimplementa peor lo que da `interrupt()` + checkpointer.

## Referencias

- `use_case_regwatch.md` → "Phase 7c — Human-in-the-Loop", `graph/nodes/human_review.py`,
  "Ensamblaje Final" (checkpointer y `Command(resume=...)`), "Phase 11" (UI /resume).
- Curso: Block 6 (LangGraph HITL, checkpoints), Block 12 (HITL approval nodes).
