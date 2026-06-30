import logging

from config import langfuse

logger = logging.getLogger(__name__)

FEW_SHOT_EXAMPLES = """
## Ejemplos de análisis

### Ejemplo 1
Política: "Los datos de clientes se almacenan indefinidamente en nuestros servidores."
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

### Ejemplo 2
Política: "El cliente puede solicitar la eliminación de sus datos enviando un email."
Regulación relevante: GDPR Art. 17 — Derecho de supresión

```json
{
  "gaps": [
    {
      "regulation_ref": "GDPR Art. 17",
      "gap_description": "No se especifica el plazo máximo de respuesta (30 días según GDPR).",
      "risk_level": "MEDIUM",
      "remediation": "Especificar que la solicitud será atendida en un máximo de 30 días naturales.",
      "confidence": 0.90
    }
  ]
}
```
"""

SYSTEM_PROMPT_V2 = f"""Eres un experto en compliance de regulación financiera europea (GDPR, MiFID II, AML).
Analiza el documento de política interna proporcionado e identifica todos los gaps regulatorios.

{FEW_SHOT_EXAMPLES}

## Instrucciones
- Devuelve ÚNICAMENTE JSON válido con la estructura mostrada en los ejemplos.
- regulation_ref DEBE seguir el formato exacto: "<Regulación> Art. <número>(<subnúmero>)"
- risk_level: HIGH | MEDIUM | LOW
- confidence: float entre 0 y 1
- Si no hay gaps, devuelve {{"gaps": []}}
"""


def ensure_prompts() -> None:
    try:
        langfuse.get_prompt("compliance-analyzer", label="staging")
        logger.info("Prompt compliance-analyzer@staging already exists, skipping")
        return
    except Exception:
        pass
    langfuse.create_prompt(
        name="compliance-analyzer",
        prompt=SYSTEM_PROMPT_V2,
        labels=["staging", "production"],
        config={"temperature": 0.1},
    )
    logger.info("Prompt compliance-analyzer registrado con labels staging + production")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    ensure_prompts()
