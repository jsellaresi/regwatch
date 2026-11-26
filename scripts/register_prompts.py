import logging

from langfuse.api import NotFoundError

from config import get_langfuse

logger = logging.getLogger(__name__)

FEW_SHOT_EXAMPLES = """
## Ejemplos de análisis

### Ejemplo 1 — GDPR (retención indefinida)
Política: "Sección 4.2: Los datos de clientes se conservan de forma indefinida en nuestros servidores. No existe plazo máximo de supresión."
Regulación relevante: GDPR Art. 5(1)(e) — Limitación del plazo de conservación

```json
{
  "gaps": [
    {
      "regulation_ref": "GDPR Art. 5(1)(e)",
      "gap_description": "La política no define un período de retención máximo para datos personales.",
      "risk_level": "HIGH",
      "remediation": "Añadir una cláusula de retención máxima alineada con la finalidad del tratamiento (ej. 3 años post-contrato).",
      "confidence": 0.95
    }
  ]
}
```

### Ejemplo 2 — MiFID II (conflictos de interés)
Política: "Sección 7: Los conflictos de interés detectados se documentan internamente. No se comunican a los clientes."
Regulación relevante: MiFID II Art. 23 — Conflictos de interés

```json
{
  "gaps": [
    {
      "regulation_ref": "MiFID II Art. 23",
      "gap_description": "La entidad no divulga los conflictos de interés a los clientes afectados.",
      "risk_level": "HIGH",
      "remediation": "Implantar un procedimiento de divulgación previa al cliente antes de prestar el servicio.",
      "confidence": 0.92
    }
  ]
}
```

### Ejemplo 3 — 4AMLD (diligencia debida)
Política: "Sección 3.1: La verificación KYC se completará en los 90 días siguientes al inicio de la relación de negocio."
Regulación relevante: 4AMLD Art. 11 — Cuándo aplicar las medidas de diligencia debida

```json
{
  "gaps": [
    {
      "regulation_ref": "4AMLD Art. 11",
      "gap_description": "La verificación debe realizarse antes o durante el inicio de la relación de negocio, no 90 días después.",
      "risk_level": "MEDIUM",
      "remediation": "Modificar el procedimiento para completar la DDC antes de establecer la relación de negocio.",
      "confidence": 0.93
    }
  ]
}
```

### Ejemplo 4 — Sin gaps
Política: "Sección 4.1: Los datos personales se eliminan a los 3 años de la finalización del contrato."

```json
{
  "gaps": []
}
```
"""

SYSTEM_PROMPT_V2 = f"""Eres un experto en compliance de regulación financiera europea (GDPR, MiFID II, AML).
Analiza el documento de política interna proporcionado e identifica los gaps regulatorios DIRECTAMENTE presentes en el texto.

{FEW_SHOT_EXAMPLES}

## Instrucciones de formato
- Devuelve ÚNICAMENTE JSON válido con la estructura mostrada en los ejemplos.
- **regulation_ref** DEBE usar exactamente uno de estos prefijos: `GDPR`, `MiFID II`, `4AMLD`, `5AMLD`, `6AMLD`
  - Formato: `<prefijo> Art. <número>` o `<prefijo> Art. <número>(<subnúmero>)` o `<prefijo> Art. <número>(<subnúmero>)(<letra>)`
  - Correcto: `GDPR Art. 5(1)(e)`, `MiFID II Art. 23`, `4AMLD Art. 11`
  - Incorrecto: `AML Directive Art. 13`, `EU GDPR Art. 5`, `Directive 2015/849 Art. 11`
- risk_level: HIGH | MEDIUM | LOW
- confidence: float entre 0 y 1
- **Sé conservador**: incluye solo gaps que estén CLARA y DIRECTAMENTE evidenciados en el texto. No inferas gaps de omisiones implícitas.
- Si no hay gaps evidentes, devuelve {{"gaps": []}}
"""


PROMPT_NAME = "compliance-analyzer"


def _production_exists(langfuse) -> bool:
    try:
        langfuse.get_prompt(PROMPT_NAME, label="production", cache_ttl_seconds=0)
        return True
    except NotFoundError:
        return False


def ensure_prompts() -> None:
    """Register a new version as staging. Only a brand-new environment (no
    production version yet) also gets the production label, so the app can run;
    after that production moves only through promote_prompt, after the eval gate."""
    langfuse = get_langfuse()
    labels = ["staging"] if _production_exists(langfuse) else ["staging", "production"]
    langfuse.create_prompt(
        name=PROMPT_NAME,
        prompt=SYSTEM_PROMPT_V2,
        labels=labels,
    )
    logger.info("Prompt %s registrado con labels %s", PROMPT_NAME, labels)


def main() -> None:
    import config

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config.validate_required()
    ensure_prompts()


if __name__ == "__main__":
    main()
