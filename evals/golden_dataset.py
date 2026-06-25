GOLDEN_CASES = [
    {
        "id": "gdpr-retention-001",
        "document_excerpt": "Los datos de clientes se almacenan por tiempo indefinido.",
        "expected_gaps": [
            {"regulation_ref": "GDPR Art. 5(1)(e)", "risk_level": "HIGH"}
        ],
    },
    {
        "id": "mifid-disclosure-001",
        "document_excerpt": "Los conflictos de interés se gestionan internamente sin divulgación al cliente.",
        "expected_gaps": [
            {"regulation_ref": "MiFID II Art. 23", "risk_level": "HIGH"}
        ],
    },
    {
        "id": "aml-kyc-001",
        "document_excerpt": "La verificación de identidad se realiza en los primeros 90 días.",
        "expected_gaps": [
            {"regulation_ref": "AML6 Art. 13", "risk_level": "MEDIUM"}
        ],
    },
    {
        "id": "no-gap-001",
        "document_excerpt": "Los datos personales se eliminan a los 3 años de fin de contrato.",
        "expected_gaps": [],
    },
]
