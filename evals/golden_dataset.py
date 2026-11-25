GOLDEN_CASES = [
    {
        "id": "gdpr-retention-001",
        # Excerpt focused only on indefinite retention, so the model doesn't
        # add other GDPR articles (minimisation, legal basis, etc.)
        "document_excerpt": (
            "Sección 4.2 — Retención de datos: La empresa conserva todos los registros "
            "de clientes de forma indefinida en sus servidores. No existe política de "
            "supresión ni plazo máximo de conservación definido para ninguna categoría de datos."
        ),
        "expected_gaps": [
            {"regulation_ref": "GDPR Art. 5(1)(e)", "risk_level": "HIGH"}
        ],
    },
    {
        "id": "mifid-disclosure-001",
        "document_excerpt": (
            "Sección 7 — Conflictos de interés: Los conflictos de interés detectados "
            "se documentan en un registro interno. La entidad no comunica ni divulga "
            "dichos conflictos a los clientes afectados antes ni durante la prestación "
            "del servicio de inversión."
        ),
        "expected_gaps": [
            {"regulation_ref": "MiFID II Art. 23", "risk_level": "HIGH"}
        ],
    },
    {
        "id": "aml-kyc-001",
        # 4AMLD Art. 11 requires customer due diligence to be applied BEFORE or
        # during the start of the business relationship, not 90 days after.
        "document_excerpt": (
            "Sección 3.1 — Diligencia debida: La verificación de la identidad del cliente "
            "y la recogida de documentación KYC se completarán dentro de los 90 días "
            "naturales siguientes al inicio de la relación de negocio."
        ),
        "expected_gaps": [
            {"regulation_ref": "4AMLD Art. 11", "risk_level": "MEDIUM"}
        ],
    },
    {
        "id": "no-gap-001",
        "document_excerpt": (
            "Sección 4.1 — Retención de datos: Los datos personales de clientes se "
            "conservan durante un máximo de 3 años desde la finalización del contrato, "
            "tras lo cual son eliminados de forma segura conforme al procedimiento PR-042."
        ),
        "expected_gaps": [],
    },
]
