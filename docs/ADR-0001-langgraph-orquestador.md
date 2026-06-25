# ADR-0001: LangGraph (StateGraph) como orquestador central

- **Estado:** Aceptada
- **Fecha:** 2026-06-25

## Contexto

RegWatch no es un flujo lineal de prompt→respuesta. El pipeline necesita:

- **Ramas condicionales** (guardrail bloquea / pasa; judge aprueba / reintenta).
- **Ejecución en paralelo** (retrieval híbrido y sub-agente de tools a la vez).
- **Ciclos acotados** (loop de reintento del análisis, loop del sub-agente de tools).
- **Pausa y reanudación** para human-in-the-loop (ver [ADR-0011](ADR-0011-human-in-the-loop-interrupt.md)).
- **Estado tipado y compartido** entre nodos.

Una cadena LCEL (`prompt | llm | parser`) es excelente para flujos lineales, pero no modela
ramificación, ciclos ni persistencia de estado de forma nativa. Orquestar esto "a mano" con
funciones Python y `if/else` reimplementaría —peor— lo que LangGraph ya ofrece.

## Decisión

Usar **LangGraph `StateGraph`** como orquestador central. El estado es un `TypedDict`
(`RegWatchState`), los nodos son funciones puras `state -> dict`, y el control de flujo se expresa
con `add_edge`, `add_conditional_edges` y un checkpointer para persistencia.

## Consecuencias

**Positivas**
- Fan-out/fan-in, conditional edges y ciclos son primitivas de primera clase.
- El checkpointer habilita HITL (pausar/retomar) y tolerancia a fallos sin código extra.
- El grafo es inspeccionable y se puede emitir por streaming nodo a nodo (alimenta la UI, Phase 11).
- Encaja con el resto del stack LangChain (tools, modelos, LangFuse).

**Negativas / trade-offs**
- Curva de aprendizaje mayor que una cadena LCEL simple.
- El estado compartido obliga a pensar en reducers cuando dos ramas escriben la misma clave.

## Alternativas consideradas

- **Cadenas LCEL puras:** descartadas; no modelan ramificación/ciclos/persistencia.
- **Orquestación manual en Python:** descartada; reimplementa el scheduler de LangGraph con más bugs.
- **Frameworks de agentes genéricos (p. ej. CrewAI/AutoGen):** descartados; menos control explícito
  del grafo y de la persistencia que necesita un caso de compliance auditable.

## Referencias

- `use_case_regwatch.md` → "Ensamblaje Final: El Grafo LangGraph", "Estado Global del Grafo".
- Curso: Block 6 (LangGraph), Block 4 (LangChain/LCEL).
