# ADR-0003: Recuperación híbrida (pgvector + BM25 con Reciprocal Rank Fusion)

- **Estado:** Aceptada
- **Fecha:** 2026-06-25

## Contexto

El analizador necesita recuperar los artículos regulatorios relevantes para una política. Hay dos
naturalezas de consulta que conviven:

- **Semántica:** "almacenamos datos indefinidamente" debe encontrar el principio de *limitación del
  plazo de conservación* aunque no comparta palabras exactas. Esto lo resuelve la búsqueda vectorial.
- **Léxica exacta:** referencias como "Art. 17" o términos legales precisos ("responsable del
  tratamiento") donde el *match* exacto importa. Aquí la búsqueda vectorial a veces falla y BM25
  acierta.

Usar solo una de las dos deja casos sin cubrir.

## Decisión

Combinar **búsqueda semántica (pgvector)** y **búsqueda léxica (BM25)** mediante un
`EnsembleRetriever` con **Reciprocal Rank Fusion** (pesos 50/50). Ambos recuperan k=20 y la fusión
produce el conjunto que luego refina el reranking ([ADR-0005](ADR-0005-reranking-cross-encoder.md)).

Decisión asociada: BM25 se construye **una sola vez en arranque** sobre **los mismos chunks** ya
embebidos (leídos de pgvector), no sobre los PDFs crudos en cada request — garantiza que ambos
retrievers operan sobre idéntico corpus y elimina un coste por petición.

## Consecuencias

**Positivas**
- Cobertura de consultas semánticas y de coincidencias exactas (citas, términos legales).
- RRF es robusto: no requiere calibrar scores entre sistemas heterogéneos, solo rangos.
- Construcción única de BM25 → latencia por request baja y corpus consistente.

**Negativas / trade-offs**
- Mantener dos índices (vectorial + BM25 en memoria) consume algo más de RAM en el proceso.
- BM25 en memoria debe reconstruirse si el corpus cambia (re-ingesta → reinicio o recarga).

**Descomposición de query (implementada):** `graph/nodes/retrieve_regulations.py` inicialmente usaba
`extracted_text[:2000]` como *única* query — los primeros 2.000 caracteres del documento de política,
embebidos de una sola vez. Cuando una política mezcla varios temas (protección de datos, idoneidad
MiFID, KYC/AML) en secciones distintas, o cuando el texto relevante para un gap cae después del
carácter 2.000, ese texto nunca entraba siquiera en el conjunto de k=20 candidatos — un artículo no
recuperado es un gap no detectado, no un "false negative" inocuo en compliance.

Corregido dividiendo el documento en queries por sección/cláusula con
`RecursiveCharacterTextSplitter` (separadores `"\nSección"`, `"\nSection"`, `"\nCláusula"`,
`"\nClause"`, `"\n\n"`, `"\n"` — mismo paquete que ya usa `scripts/ingest_regulations.py` para trocear
las regulaciones del corpus), invocando `get_hybrid_retriever().invoke(query)` una vez por sección
(tope de `MAX_SECTIONS = 8` por coste/latencia) y deduplicando el resultado combinado por
`(regulation, content)`. Un documento que cabe en una sola query (`<= 2.000` caracteres) sigue
haciendo exactamente una llamada de recuperación — comportamiento sin cambios para documentos cortos.
El reranking ([ADR-0005](ADR-0005-reranking-cross-encoder.md)) sigue reduciendo el conjunto —ahora más
diverso— a `TOP_N = 5` sin cambios propios: la descomposición mejora qué entra al *pool* de candidatos,
no cómo se recorta al final. Si cinco chunks siguen sin cubrir todos los temas de una política
compleja tras esta corrección, subir `TOP_N` es un ajuste de sintonía pendiente, no parte de este ADR.

## Alternativas consideradas

- **Solo semántico (pgvector):** descartado; falla en citas/términos exactos.
- **Solo léxico (BM25):** descartado; no captura sinónimos ni paráfrasis.
- **Fusión ponderada por score normalizado:** descartada frente a RRF por la dificultad de comparar
  escalas de score entre vectorial y BM25.

## Referencias

- `use_case_regwatch.md` → "Phase 3 — RAG", `retriever.py`, `graph/nodes/retrieve_regulations.py`.
- Curso: Block 11 (RAG), Block 12 (Advanced RAG: hybrid retrieval).
