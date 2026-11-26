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
    # ── Cases below: each expected article was checked against the text of the regulation in
    # data/. Scoring is article-level, so the paragraph in the label is documentation. The legal
    # labels are the maintainer's call; a case the model reads differently is a signal to review it.
    # GDPR
    {
        "id": "gdpr-breach-notification-001",
        "document_excerpt": (
            "Sección 9.1 — Incidentes de seguridad: Cuando se produce una violación de la seguridad "
            "de los datos personales, el equipo de seguridad la investiga internamente. La "
            "notificación a la autoridad de control se valora caso por caso, no existe un plazo "
            "máximo definido y en la práctica se realiza semanas después de detectar el incidente."
        ),
        "expected_gaps": [{"regulation_ref": "GDPR Art. 33(1)", "risk_level": "HIGH"}],
    },
    {
        "id": "gdpr-dpo-001",
        "document_excerpt": (
            "Sección 2.4 — Gobierno de datos: La entidad realiza una observación habitual y "
            "sistemática del comportamiento de sus clientes a gran escala. No ha designado un "
            "delegado de protección de datos porque la dirección considera que no es necesario."
        ),
        "expected_gaps": [{"regulation_ref": "GDPR Art. 37(1)", "risk_level": "HIGH"}],
    },
    {
        "id": "gdpr-dpia-001",
        "document_excerpt": (
            "Sección 6.3 — Nuevos tratamientos: Los proyectos que implican un tratamiento de datos "
            "personales con alto riesgo para los derechos de los clientes se aprueban sin realizar "
            "ninguna evaluación de impacto relativa a la protección de datos."
        ),
        "expected_gaps": [{"regulation_ref": "GDPR Art. 35(1)", "risk_level": "HIGH"}],
    },
    {
        "id": "gdpr-consent-withdrawal-001",
        "document_excerpt": (
            "Sección 5.3 — Marketing: Una vez que el cliente ha otorgado su consentimiento para "
            "recibir comunicaciones comerciales, no existe ningún procedimiento para retirarlo; "
            "las solicitudes de baja se ignoran."
        ),
        "expected_gaps": [{"regulation_ref": "GDPR Art. 7(3)", "risk_level": "HIGH"}],
    },
    # MiFID II
    {
        "id": "mifid-best-execution-001",
        "document_excerpt": (
            "Sección 8.2 — Ejecución de órdenes: Las órdenes de los clientes minoristas se envían "
            "siempre al centro de ejecución que abona a la entidad la mayor retrocesión, sin "
            "comparar precio, costes, rapidez ni probabilidad de ejecución entre centros alternativos."
        ),
        "expected_gaps": [{"regulation_ref": "MiFID II Art. 27(1)", "risk_level": "HIGH"}],
    },
    {
        "id": "mifid-suitability-001",
        "document_excerpt": (
            "Sección 7.4 — Asesoramiento: Los asesores recomiendan productos financieros complejos "
            "a clientes minoristas sin recabar información sobre sus conocimientos y experiencia, "
            "su situación financiera ni sus objetivos de inversión."
        ),
        "expected_gaps": [{"regulation_ref": "MiFID II Art. 25(2)", "risk_level": "HIGH"}],
    },
    {
        "id": "mifid-recording-001",
        "document_excerpt": (
            "Sección 8.7 — Registro de comunicaciones: Las conversaciones telefónicas y las "
            "comunicaciones electrónicas relacionadas con órdenes de clientes no se graban ni se "
            "conservan; solo se guardan los tickets de las operaciones cerradas."
        ),
        "expected_gaps": [{"regulation_ref": "MiFID II Art. 16(7)", "risk_level": "MEDIUM"}],
    },
    # AML
    {
        "id": "aml-pep-001",
        "document_excerpt": (
            "Sección 3.5 — Personas con responsabilidad pública: La entidad no dispone de ningún "
            "procedimiento para determinar si un cliente o su titular real es una persona del medio "
            "político, ni aplica medidas reforzadas de diligencia debida a estas personas."
        ),
        "expected_gaps": [{"regulation_ref": "4AMLD Art. 20", "risk_level": "HIGH"}],
    },
    {
        "id": "aml-str-001",
        "document_excerpt": (
            "Sección 6.2 — Operaciones sospechosas: Las operaciones sospechosas de blanqueo de "
            "capitales se registran en un informe interno, pero la entidad no las comunica a la "
            "unidad de información financiera por considerar suficiente el registro interno."
        ),
        "expected_gaps": [{"regulation_ref": "4AMLD Art. 33(1)", "risk_level": "HIGH"}],
    },
    {
        "id": "aml-recordkeeping-001",
        "document_excerpt": (
            "Sección 3.9 — Conservación de documentos: Los documentos de identificación y la "
            "información de diligencia debida de los clientes se eliminan a los doce meses de "
            "finalizar la relación de negocios."
        ),
        "expected_gaps": [{"regulation_ref": "4AMLD Art. 40(1)", "risk_level": "MEDIUM"}],
    },
    # Compliant policies and a borderline one: the model must not invent gaps
    {
        "id": "no-gap-gdpr-001",
        "document_excerpt": (
            "Sección 9.1 — Incidentes de seguridad: Toda violación de la seguridad de los datos "
            "personales se notifica a la autoridad de control sin dilación indebida y, a más "
            "tardar, 72 horas después de tener constancia de ella, salvo que sea improbable que "
            "entrañe un riesgo para los derechos de los interesados. El delegado de protección de "
            "datos supervisa el proceso."
        ),
        "expected_gaps": [],
    },
    {
        "id": "no-gap-aml-001",
        "document_excerpt": (
            "Sección 3.1 — Diligencia debida: La identidad del cliente y del titular real se "
            "verifica antes de establecer la relación de negocios. Se determina si el cliente es "
            "una persona del medio político y, en ese caso, se aplican medidas reforzadas. Las "
            "operaciones sospechosas se comunican sin demora a la UIF y los documentos se "
            "conservan cinco años tras el fin de la relación."
        ),
        "expected_gaps": [],
    },
    {
        "id": "no-gap-legal-retention-001",
        "document_excerpt": (
            "Sección 4.3 — Conservación contable: Los registros de facturación se conservan diez "
            "años por obligación legal fiscal y mercantil; transcurrido ese plazo se suprimen de "
            "forma segura. No se utilizan para ninguna otra finalidad."
        ),
        "expected_gaps": [],
    },
]
