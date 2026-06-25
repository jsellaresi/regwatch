# ADR-0014: Extracción multimodal con Claude Vision

- **Estado:** Aceptada
- **Fecha:** 2026-06-25

## Contexto

Las políticas internas llegan como PDF, pero no siempre son PDFs "digitales" con texto
seleccionable: muchas son **escaneadas** (documentos firmados, páginas con tablas, sellos). Un
extractor de texto puro (`page.get_text()`) devuelve vacío o basura en esas páginas, y un OCR clásico
(p. ej. Tesseract) sufre con tablas y maquetaciones complejas, perdiendo estructura clave para el
análisis de compliance.

## Decisión

Extracción **híbrida por página** en `multimodal_extract`:

- Si la página tiene texto digital (`page.get_text()` no vacío) → se usa directamente (rápido y gratis).
- Si está escaneada → se renderiza a imagen (PyMuPDF, 200 dpi) y se envía a **Claude Vision**, que
  extrae el texto **preservando la estructura de tablas en markdown**.

## Consecuencias

**Positivas**
- Soporta tanto PDFs digitales como escaneados sin un pipeline de OCR aparte.
- Claude Vision conserva tablas y estructura mejor que un OCR tradicional, lo que mejora el material
  que recibe el analizador.
- Coste optimizado: solo las páginas escaneadas pagan una llamada a Vision; las digitales son gratis.

**Negativas / trade-offs**
- Las páginas escaneadas añaden latencia y coste de tokens de visión.
- A 200 dpi documentos muy degradados pueden perder calidad; ajustable subiendo dpi (más coste).
- Dependencia del proveedor para la capacidad multimodal.

## Alternativas consideradas

- **Solo `get_text()`:** descartado; falla por completo en PDFs escaneados.
- **OCR clásico (Tesseract):** descartado; peor con tablas/maquetación y sin comprensión semántica.
- **Vision en todas las páginas:** descartado; coste innecesario en páginas digitales que ya traen texto.

## Referencias

- `use_case_regwatch.md` → "Phase 2 — Extracción Multimodal", `graph/nodes/multimodal_extract.py`.
- Curso: Block 9 (closed source models, multimodal).
