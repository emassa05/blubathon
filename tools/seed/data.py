"""Contenido ficticio de la demo (SPEC 12.3, TAREAS M0 P2.5).

Nombres, textos y documentos son inventados para la demostración. Los documentos
del catálogo fixture llevan `publisher=FIXTURE_DEMO` y
`rights_basis=fixture_demo_only` justamente para que nadie los confunda con
literatura real de la allowlist de `SPEC 9.2`.
"""

from __future__ import annotations

from tools.seed import ids

TENANTS = (
    {"tenant_id": ids.TENANT_A, "name": "Centro Faro Demo"},
    {"tenant_id": ids.TENANT_B, "name": "Otra Organización Demo"},
)

USERS = (
    {
        "user_id": ids.CAREGIVER_A,
        "tenant_id": ids.TENANT_A,
        "display_name": "Ana Ríos (cuidadora ficticia)",
        "roles": ("caregiver",),
    },
    {
        "user_id": ids.PROFESSIONAL_A,
        "tenant_id": ids.TENANT_A,
        "display_name": "Pilar Soto (profesional ficticia)",
        "roles": ("professional",),
    },
    {
        "user_id": ids.TENANT_ADMIN_A,
        "tenant_id": ids.TENANT_A,
        "display_name": "Admin Demo A",
        "roles": ("tenant_admin",),
    },
    {
        "user_id": ids.MODEL_EVALUATOR_A,
        "tenant_id": ids.TENANT_A,
        "display_name": "Evaluador Demo A",
        "roles": ("model_evaluator",),
    },
    {
        "user_id": ids.UNACCREDITED_PROFESSIONAL_A,
        "tenant_id": ids.TENANT_A,
        "display_name": "Profesional sin acreditación (demo)",
        "roles": ("professional",),
    },
    {
        "user_id": ids.CAREGIVER_B,
        "tenant_id": ids.TENANT_B,
        "display_name": "Cuidador Demo B",
        "roles": ("caregiver",),
    },
    {
        "user_id": ids.PROFESSIONAL_B,
        "tenant_id": ids.TENANT_B,
        "display_name": "Profesional Demo B",
        "roles": ("professional",),
    },
    {
        "user_id": ids.TENANT_ADMIN_B,
        "tenant_id": ids.TENANT_B,
        "display_name": "Admin Demo B",
        "roles": ("tenant_admin",),
    },
)

SUBJECTS = (
    {
        "subject_id": ids.SUBJECT_ANA,
        "tenant_id": ids.TENANT_A,
        "display_label": "Niña demo 1",
        "care_mode": "home_and_therapy",
        "sensory_profile_tags": ["auditory_hypersensitive"],
        "communication_support_tags": ["visual_schedule"],
        "contraindication_tags": [],
    },
    {
        "subject_id": ids.SUBJECT_BETO,
        "tenant_id": ids.TENANT_A,
        "display_label": "Niño demo 2",
        "care_mode": "home_only",
        "sensory_profile_tags": ["tactile_seeking"],
        "communication_support_tags": [],
        "contraindication_tags": ["no_deep_pressure"],
    },
    {
        "subject_id": ids.SUBJECT_SIN_GRANT,
        "tenant_id": ids.TENANT_A,
        "display_label": "Niña demo 3 (sin grant)",
        "care_mode": "home_only",
        "sensory_profile_tags": [],
        "communication_support_tags": [],
        "contraindication_tags": [],
    },
    {
        "subject_id": ids.SUBJECT_TENANT_B,
        "tenant_id": ids.TENANT_B,
        "display_label": "Niño demo de otra organización",
        "care_mode": "home_only",
        "sensory_profile_tags": [],
        "communication_support_tags": [],
        "contraindication_tags": [],
    },
)

CAREGIVER_CAPABILITIES = (
    "subject_read",
    "daily_observation_write",
    "form_submit",
    "outcome_report",
    "execution_record",
)
PROFESSIONAL_CAPABILITIES = (
    "subject_read",
    "daily_observation_write",
    "form_submit",
    "outcome_report",
    "recommendation_review",
    "execution_record",
    "evaluation_read",
)

GRANTS = (
    (ids.CAREGIVER_A, ids.SUBJECT_ANA, CAREGIVER_CAPABILITIES),
    (ids.CAREGIVER_A, ids.SUBJECT_BETO, CAREGIVER_CAPABILITIES),
    (ids.PROFESSIONAL_A, ids.SUBJECT_ANA, PROFESSIONAL_CAPABILITIES),
    (ids.PROFESSIONAL_A, ids.SUBJECT_BETO, PROFESSIONAL_CAPABILITIES),
    (ids.UNACCREDITED_PROFESSIONAL_A, ids.SUBJECT_ANA, PROFESSIONAL_CAPABILITIES),
    (ids.CAREGIVER_B, ids.SUBJECT_TENANT_B, CAREGIVER_CAPABILITIES),
    (ids.PROFESSIONAL_B, ids.SUBJECT_TENANT_B, PROFESSIONAL_CAPABILITIES),
)

# El objetivo demo es una definición versionada aparte, con `data_origin`
# sintético. No se hace pasar por un label real (SPEC 4.3).
TARGET_DEMO = {
    "target_definition_version": ids.TARGET_DEMO_FIXTURE,
    "scope": "demo_fixture",
    "question_es": (
        "¿Ocurrió una desregulación mayor en las últimas 24 horas, según las anclas "
        "acordadas para esta demostración?"
    ),
    "severity_anchors_es": [
        "No ocurrió: el día transcurrió dentro de lo habitual para esta persona.",
        "Ocurrió: hubo un episodio que requirió detener la actividad y dar apoyo "
        "sostenido por más de 20 minutos.",
    ],
    "eligible_reporter_roles": ["caregiver", "professional"],
    "eligible_source_mappings": [],
    "evidence_basis": (
        "Definición ficticia de demostración. No proviene de un consenso clínico ni "
        "de una guía publicada."
    ),
}

FIXTURE_DOCUMENT = {
    "source_id": "fixture-doc-001",
    "publisher": "FIXTURE_DEMO",
    "title": "Documento ficticio de demostración sobre rutinas y sueño",
    "document_version": "1.0.0",
    "publication_date": "2026-01-15",
    "canonical_url": "https://example.invalid/faro/fixture-doc-001/v1",
    "rights_basis": "fixture_demo_only",
    "language": "es",
}

FIXTURE_CHUNKS = (
    {
        "locator": "sección 2, párrafo 3",
        "text": (
            "Cuando el sueño se interrumpe, conviene revisar primero las condiciones "
            "del entorno antes de cambiar la rutina completa."
        ),
    },
    {
        "locator": "sección 4, párrafo 1",
        "text": (
            "Anticipar los cambios de actividad con apoyos visuales reduce la "
            "necesidad de correcciones durante la transición."
        ),
    },
)

FIXTURE_STRATEGIES = (
    {
        "key": "sleep_environment",
        "purpose_es": "Revisar el entorno de sueño antes de cambiar la rutina.",
        "action_text_es": (
            "Antes de modificar la rutina, revisen juntos luz, ruido y temperatura del "
            "lugar donde duerme."
        ),
        "claim_text_es": "revisen juntos luz, ruido y temperatura del lugar donde duerme",
        "chunk_index": 0,
        "quoted_text": (
            "conviene revisar primero las condiciones del entorno antes de cambiar la "
            "rutina completa"
        ),
        "required_approver_role": "professional",
        "allowed_executor_roles": ["caregiver", "professional"],
        "predicate": {
            "required_field_values": {"sleep_quality": ["interrupted", "sleep_onset_difficulty"]},
            "excluded_field_values": {},
            "required_context_tags": [],
            "excluded_context_tags": [],
            "required_profile_tags": [],
            "contraindication_tags": ["no_deep_pressure"],
        },
    },
    {
        "key": "visual_transition",
        "purpose_es": "Anticipar transiciones con un apoyo visual acordado.",
        "action_text_es": (
            "Avisen el cambio de actividad con el apoyo visual acordado, unos minutos "
            "antes de que ocurra."
        ),
        "claim_text_es": "con el apoyo visual acordado, unos minutos antes",
        "chunk_index": 1,
        "quoted_text": (
            "Anticipar los cambios de actividad con apoyos visuales reduce la "
            "necesidad de correcciones durante la transición."
        ),
        "required_approver_role": "professional",
        "allowed_executor_roles": ["caregiver", "professional"],
        "predicate": {
            "required_field_values": {},
            "excluded_field_values": {"alertness": ["other"]},
            "required_context_tags": [],
            "excluded_context_tags": [],
            "required_profile_tags": [],
            "contraindication_tags": [],
        },
    },
)

SET_PREDICATE = {
    "required_field_values": {},
    "excluded_field_values": {},
    "required_context_tags": [],
    "excluded_context_tags": [],
    "required_profile_tags": [],
    "contraindication_tags": [],
}
