# ADR-0005: Reranking con cross-encoder

- **Estado:** Aceptada
- **Fecha:** 2026-06-25

## Contexto

La recuperación híbrida ([ADR-0003](ADR-0003-recuperacion-hibrida.md)) devuelve un top-k razonable,
pero ordenado por una fusión de rangos (RRF), no por relevancia real evaluada conjuntamente entre
consulta y documento. Los *bi-encoders* (embeddings) codifican consulta y documento por separado;
pierden matices de interacción.

En compliance la **precisión del contexto es crítica**: si el artículo realmente pertinente no queda
en el top que se le pasa al analizador, la cita saldrá mal y la métrica `legal_accuracy` del juez
caerá. Pasar muchos chunks "por si acaso" tampoco es gratis: infla tokens, coste y latencia, y
diluye la atención del modelo.

## Decisión

Añadir un nodo `rerank` con un **cross-encoder** que reordena el resultado del híbrido y se queda
con el **top-5**. El patrón es: **recuperar k=20 (híbrido) → rerank → top-5 al analizador**.

- **Primario:** Cohere Rerank (`rerank-multilingual-v3.0`, multilingüe por el corpus en español).
- **Alternativa local:** `BAAI/bge-reranker-v2-m3` (sin coste por llamada; requiere GPU/CPU).

## Consecuencias

**Positivas**
- Sube directamente `legal_accuracy`: el artículo correcto llega arriba.
- **Coste neto del LLM baja:** se pasan 5 chunks en vez de 10–20 → menos tokens de entrada al
  analizador, que es la llamada más cara del pipeline.
- Recuperar amplio (k=20) y refinar evita el dilema "k pequeño pierde recall / k grande mete ruido".

**Negativas / trade-offs**
- Latencia añadida: ~100–400 ms con Cohere hosted; ~1–2 s con BGE local en CPU.
- Cohere introduce coste y dependencia externa (~$2 / 1.000 búsquedas). La alternativa local lo
  elimina a cambio de infraestructura.

## Alternativas consideradas

- **Sin reranking (usar el top del híbrido):** descartado; menor precisión en un dominio donde un
  artículo equivocado es un error grave.
- **Subir k y pasar todo al LLM:** descartado; más coste/latencia y peor señal-ruido que rerank+top-5.
- **Reranking con LLM (listwise por prompt):** descartado por coste y latencia frente a un
  cross-encoder especializado.

## Referencias

- Código: `graph/nodes/rerank.py`.
- Curso: Block 12 (Advanced RAG: reranking).
