# ADR-0010: Agent-as-Judge con modelo distinto

- **Estado:** Aceptada
- **Fecha:** 2026-06-25

## Contexto

La calidad de un informe de compliance no se puede garantizar solo con el modelo que lo genera: los
LLMs tienden a evaluar favorablemente su propio output (sesgo de auto-complacencia). Hace falta un
control de calidad automático y objetivo antes de emitir el informe o abrir tickets.

## Decisión

Introducir un nodo **Agent-as-Judge** que puntúa el informe en tres dimensiones (`legal_accuracy`,
`citation_quality`, `actionability`) y decide `approved`. Dos decisiones clave:

1. **Modelo distinto al analizador:** el analizador usa `claude-sonnet-4-6`; el juez usa `gpt-4o`.
   Un evaluador independiente reduce el sesgo de evaluar el propio razonamiento.
2. **Salida estructurada** (`JudgeScores`, ver [ADR-0008](ADR-0008-salida-estructurada-pydantic.md))
   y bucle de reintento **acotado** (máx. 3): si no aprueba, reintenta el análisis; al agotar los
   intentos, **no se fuerza el paso** sino que se escala a revisión humana
   ([ADR-0011](ADR-0011-human-in-the-loop-interrupt.md)).

Los scores del juez se registran como métricas en LangFuse por traza (observabilidad y seguimiento
por versión de prompt).

## Consecuencias

**Positivas**
- Control de calidad objetivo antes de emitir; menos informes pobres en producción.
- Modelo independiente → evaluación menos sesgada que un self-check.
- Los scores alimentan el dashboard y permiten detectar regresiones por versión de prompt.

**Negativas / trade-offs**
- Coste y latencia de una segunda llamada LLM por análisis (y por reintento).
- Dependencia de un segundo proveedor (OpenAI) además de Anthropic.

## Alternativas consideradas

- **Sin juez (confiar en el analizador):** descartado; sin control de calidad automático.
- **Self-evaluation con el mismo modelo:** descartado por sesgo de auto-complacencia.
- **Solo evals offline (sin juez en runtime):** los evals (ADR-0009) protegen el *prompt*, pero no
  evalúan *cada informe concreto*; el juez en runtime es complementario, no sustituible.

## Referencias

- `use_case_regwatch.md` → "Phase 7 — Análisis + Agent as Judge + HITL", `graph/nodes/agent_judge.py`.
- Curso: Block 7 (LLM-as-a-Judge), Block 9 (multi-provider).
