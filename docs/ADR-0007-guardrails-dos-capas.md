# ADR-0007: Guardrails de dos capas con tope de reintentos

- **Estado:** Aceptada
- **Fecha:** 2026-06-25

## Contexto

El sistema recibe documentos arbitrarios subidos por usuarios y produce informes que se citan como
base de decisiones de compliance. Dos riesgos:

- **Entrada:** intentos de *prompt injection* o de extracción de datos personales (PII), o contenido
  que no es una política corporativa.
- **Salida:** citas regulatorias **alucinadas o mal formadas** (p. ej. "GDPR Artículo diecisiete"
  en vez de "GDPR Art. 17") que romperían la trazabilidad legal.

Un check puramente por LLM es flexible pero caro y lento para cada caso obvio; uno puramente por
regex es rápido pero ciego a ataques semánticos. Además, un guardrail de salida que reintente el
análisis sin límite puede entrar en bucle infinito y disparar el coste.

## Decisión

**Guardrails en dos capas:**

- **Entrada:** capa 1 *fast-path* por regex (patrones de injection y PII conocidos) → si no dispara,
  capa 2 *semantic check* con un LLM barato (`claude-haiku`). Si bloquea, el grafo va a `blocked_end`.
- **Salida:** validación del formato de cita con regex sobre el `gap_report`.

**Tope de reintentos:** el guardrail de salida lleva un contador `output_guardrail_attempt`. Tras
2 reintentos fallidos, en lugar de seguir reintentando se **escala a revisión humana**
([ADR-0011](ADR-0011-human-in-the-loop-interrupt.md)).

## Consecuencias

**Positivas**
- El fast-path resuelve los casos obvios sin coste de LLM; el semantic check cubre lo sutil.
- El tope de reintentos elimina el riesgo de bucle infinito y coste descontrolado.
- La salida nunca emite citas con formato inválido sin pasar antes por corrección o revisión humana.

**Negativas / trade-offs**
- El semantic check añade una llamada LLM (barata) en el camino de entrada.
- Los patrones regex requieren mantenimiento conforme aparecen nuevas técnicas de injection.

## Alternativas consideradas

- **Solo regex:** descartado; no detecta ataques semánticos ni contenido fuera de dominio.
- **Solo LLM:** descartado; más caro/lento para los casos triviales que la regex ya filtra.
- **Reintentar sin límite hasta cita válida:** descartado; bucle infinito y coste. Se acota y escala.

## Referencias

- `use_case_regwatch.md` → "Phase 4 — Guardrails", `graph/nodes/guardrails.py`.
- Curso: Block 2 (prompt safety), Block 6 (conditional edges).
