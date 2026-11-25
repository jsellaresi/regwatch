# ADR-0014: Multimodal extraction with Claude Vision

- **Status:** Accepted
- **Date:** 2026-06-25

## Context

Internal policies arrive as PDFs, but they are not always "digital" PDFs with selectable text: many are
**scanned** (signed documents, pages with tables, stamps). A pure text extractor (`page.get_text()`) returns
empty or garbled output on those pages, and classic OCR (e.g. Tesseract) struggles with tables and complex
layouts, losing structure that is key for compliance analysis.

## Decision

**Hybrid per-page** extraction in `multimodal_extract`:

- If the page has digital text (`page.get_text()` is not empty) → it is used directly (fast and free).
- If the page is scanned → it is rendered to an image (PyMuPDF, 200 dpi) and sent to **Claude Vision**,
  which extracts the text **preserving table structure in markdown**.

## Consequences

**Positive**
- Supports both digital and scanned PDFs without a separate OCR pipeline.
- Claude Vision preserves tables and structure better than traditional OCR, which improves the material the
  analyzer receives.
- Cost-optimized: only scanned pages incur a Vision call; digital pages are free.

**Negative / trade-offs**
- Scanned pages add latency and vision-token cost.
- At 200 dpi, heavily degraded documents may lose quality; tunable by raising the dpi (at higher cost).
- Dependency on the provider for the multimodal capability.

## Alternatives considered

- **`get_text()` only:** rejected; it fails completely on scanned PDFs.
- **Classic OCR (Tesseract):** rejected; worse with tables/layout and without semantic understanding.
- **Vision on every page:** rejected; unnecessary cost on digital pages that already contain text.

## References

- Code: `graph/nodes/multimodal_extract.py`.
- Course: Block 9 (closed source models, multimodal).
