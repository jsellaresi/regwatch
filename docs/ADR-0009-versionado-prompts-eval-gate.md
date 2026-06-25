# ADR-0009: Versionado de prompts + eval gate en CI

- **Estado:** Aceptada
- **Fecha:** 2026-06-25

## Contexto

El prompt de análisis es un artefacto vivo: cambia cuando se enmienda una regulación, cuando se
añaden few-shot examples o cuando se afina el formato de salida. Dos problemas si se trata como
texto hardcodeado en el código:

1. **Sin trazabilidad ni rollback:** no se sabe con qué versión de prompt se generó un informe (mal
   para auditoría), y revertir exige un despliegue de código.
2. **Sin red de seguridad:** un cambio de prompt puede degradar silenciosamente la calidad (menos
   recall de gaps, citas peores) y nadie se entera hasta producción.

## Decisión

- **Versionado de prompts en LangFuse Prompt Management.** El código pide el prompt por *label*
  (`production`); subir versión o hacer rollback es cambiar el label, sin tocar código. La versión
  usada se registra en la traza de cada informe (auditoría).
- **Eval gate en CI.** Un dataset *golden* con casos conocidos mide *precision/recall* y formato de
  citas. GitHub Actions ejecuta la suite contra el prompt en `staging`; **solo si pasa los umbrales**
  (precision ≥ 0.85, recall ≥ 0.80, 0 citas mal formadas) se promociona a `production`
  (`promote_prompt.py`).

## Consecuencias

**Positivas**
- Rollback instantáneo y trazabilidad prompt↔informe para auditoría.
- Ningún cambio de prompt llega a producción sin superar la barrera de calidad.
- Desacopla la iteración de prompts del ciclo de despliegue de código.

**Negativas / trade-offs**
- Dependencia de LangFuse como registro de prompts (mitigable: los prompts se pueden exportar).
- El dataset golden hay que mantenerlo y ampliarlo; un golden pobre da falsa confianza.

## Alternativas consideradas

- **Prompts hardcodeados en el código:** descartado; sin rollback rápido ni trazabilidad.
- **Versionar prompts en git sin eval gate:** mejor que hardcodear, pero no impide regresiones de
  calidad. El gate automático es el valor diferencial.

## Referencias

- `use_case_regwatch.md` → "Phase 5 — Few-Shot & Prompt Versioning", "Phase 10 — Evals + CI Gate",
  `scripts/register_prompts.py`, `scripts/promote_prompt.py`, `.github/workflows/eval_gate.yml`.
- Curso: Block 7 (prompt versioning, evals), Block 18 (CI/CD).
