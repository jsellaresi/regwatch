# ADR-0008: Salida estructurada con Pydantic

- **Estado:** Aceptada
- **Fecha:** 2026-06-25

## Contexto

El nodo de análisis y el juez deben devolver datos consumibles por el resto del grafo (gaps con
campos tipados, scores numéricos). La técnica inicial —pedir JSON en el prompt y extraerlo con
`content.find("{") ... json.loads(...)`— es frágil:

- Rompe si el modelo envuelve el JSON en texto, usa fences de markdown, o produce JSON inválido.
- Un fallo de parseo lanza una excepción que **tumba todo el grafo**.
- No valida tipos ni rangos (p. ej. `risk_level` fuera de {HIGH, MEDIUM, LOW}, `confidence` > 1).

## Decisión

Definir esquemas **Pydantic** (`Gap`, `GapReport`, `JudgeScores`) y usar
`llm.with_structured_output(Schema)`. El modelo está obligado a devolver un objeto válido (reintenta
internamente si no encaja). Además, cada nodo envuelve su cuerpo en `try/except` que escribe un
campo `error` en el estado y enruta a un final seguro, en vez de propagar la excepción.

## Consecuencias

**Positivas**
- Validación de tipos y rangos en el borde (Literal, `ge/le`), no aguas abajo.
- Elimina el parseo manual frágil y su clase entera de bugs.
- La misma definición se reutiliza en el análisis, el juez y la suite de evals (consistencia).
- Ningún nodo tumba el grafo: los errores se capturan y enrutan.

**Negativas / trade-offs**
- `with_structured_output` puede usar tool-calling/function-calling del proveedor; añade un poco de
  overhead frente a texto plano (despreciable frente a la robustez ganada).
- Acopla el esquema de salida al código; cambiarlo exige migrar consumidores (deseable: es explícito).

## Alternativas consideradas

- **Parseo manual de JSON (`json.loads`):** descartado por frágil y por tumbar el grafo.
- **`PydanticOutputParser` sobre texto:** mejor que el manual, pero `with_structured_output` da
  garantías más fuertes al delegar el formato al proveedor.

## Referencias

- `use_case_regwatch.md` → "Modelos de Salida Estructurada (Pydantic)", `graph/schemas.py`,
  `graph/nodes/analyze_compliance.py`, `graph/nodes/agent_judge.py`.
- Curso: Block 4 (parsers), Block 7 (evals consistentes).
