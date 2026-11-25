# ADR-0012: Patrón de tools — recopilar con LLM vs actuar de forma determinista

- **Estado:** Aceptada
- **Fecha:** 2026-06-25

## Contexto

RegWatch tiene tres capacidades externas (tools):

- `get_regulation_amendments` (EUR-Lex) y `web_search_regulation`: **recopilan información**.
- `create_jira_ticket`: **ejecuta una acción** con efectos secundarios (abre un ticket real).

Un error de diseño frecuente es exponer todas las tools a un agente LLM y dejar que "decida" qué
hacer, incluida la acción. En compliance, dejar que un modelo decida *si* abrir un ticket (o cuántos)
es arriesgado: efectos no deterministas, difíciles de auditar y de testear.

(Nota: la versión inicial tenía además un bug — un `ToolNode` suelto sin ningún LLM que generara
`tool_calls` y sin clave `messages` en el estado; las tools nunca se ejecutaban.)

## Decisión

Separar las tools por intención:

- **Recopilar → con LLM.** Un sub-agente `enrich_agent` con `bind_tools(ENRICH_TOOLS)` decide qué
  herramientas de información llamar y con qué argumentos, en un loop `enrich_agent ⇄ ToolNode` hasta
  que no haya más `tool_calls`. Esto requiere la clave `messages` (`add_messages`) en el estado.
- **Actuar → determinista.** `create_jira_ticket` **no** se expone al LLM. El nodo `create_tickets`
  itera los gaps HIGH/MEDIUM e invoca la tool directamente, de forma predecible y auditable.

## Consecuencias

**Positivas**
- La parte abierta/exploratoria (qué info externa traer) aprovecha la flexibilidad del LLM.
- La parte con efectos secundarios es determinista: testeable, auditable, sin sorpresas.
- Las tools de información **sí se ejecutan** (loop correcto con `messages`), corrigiendo el bug.
- `enrich_agent` corre en paralelo con el retrieval (fan-out) y se une en el análisis.

**Negativas / trade-offs**
- Dos mecanismos distintos para "usar tools" en el mismo sistema (hay que entender la distinción).
- El loop del sub-agente añade llamadas LLM cuando decide consultar fuentes externas.

## Alternativas consideradas

- **Un único agente con todas las tools (incluida JIRA):** descartado; cede el control de una acción
  con efectos secundarios al LLM, malo para auditoría y testing.
- **Todo determinista (sin sub-agente):** descartado; perdería la flexibilidad de decidir cuándo
  enriquecer con enmiendas/búsqueda según el documento.

## Referencias

- Código: `tools/regulation_tools.py`, `graph/nodes/enrich_agent.py`.
- Curso: Block 4 (LangChain tools), Block 6 (ToolNode + agentic loop).
