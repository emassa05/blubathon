"""Contenido ficticio de la demo (M0 P2.5).

Nombres, textos y documentos son inventados para la demostración. Los documentos
del catálogo fixture llevan `publisher=FIXTURE_DEMO` y
`rights_basis=fixture_demo_only` justamente para que nadie los confunda con
literatura real de la allowlist.
"""

from __future__ import annotations

from tools.seed import ids

TENANTS = (
    {"tenant_id": ids.TENANT_A, "name": "Centro Blubathon Demo"},
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
        "cohort_kind": "demo_fixture",
        "tenant_id": ids.TENANT_A,
        "display_label": "Niña demo 1",
        "care_mode": "home_and_therapy",
        "sensory_profile_tags": ["auditory_hypersensitive"],
        "communication_support_tags": ["visual_schedule"],
        "contraindication_tags": [],
    },
    {
        "subject_id": ids.SUBJECT_BETO,
        "cohort_kind": "demo_fixture",
        "tenant_id": ids.TENANT_A,
        "display_label": "Niño demo 2",
        "care_mode": "home_only",
        "sensory_profile_tags": ["tactile_seeking"],
        "communication_support_tags": [],
        "contraindication_tags": ["no_deep_pressure"],
    },
    {
        "subject_id": ids.SUBJECT_SIN_GRANT,
        "cohort_kind": "demo_fixture",
        "tenant_id": ids.TENANT_A,
        "display_label": "Niña demo 3",
        "care_mode": "home_only",
        "sensory_profile_tags": [],
        "communication_support_tags": [],
        "contraindication_tags": [],
    },
    {
        "subject_id": ids.SUBJECT_REAL,
        "tenant_id": ids.TENANT_A,
        "cohort_kind": "real_subject",
        "display_label": "Niña demo 4",
        "care_mode": "home_only",
        "sensory_profile_tags": ["auditory_hypersensitive"],
        "communication_support_tags": ["visual_schedule"],
        "contraindication_tags": [],
    },
    {
        "subject_id": ids.SUBJECT_REAL_B,
        "tenant_id": ids.TENANT_A,
        "cohort_kind": "real_subject",
        "display_label": "Niño demo 5",
        "care_mode": "home_and_therapy",
        "sensory_profile_tags": ["tactile_seeking"],
        "communication_support_tags": [],
        "contraindication_tags": [],
    },
    {
        # Solo el sueño viene mal; lo demás se responde bien. Sirve para ver la
        # recomendación de sueño aislada: con el perfil mixto la consulta trae
        # vocabulario de GI, medicación y rutina, y el fragmento que gana no es
        # el de sueño. Se siembra con `--perfil sueno` (tools.demo_history).
        "subject_id": ids.SUBJECT_SUENO,
        "tenant_id": ids.TENANT_A,
        "cohort_kind": "real_subject",
        "display_label": "Niña demo 6",
        "care_mode": "home_only",
        "sensory_profile_tags": ["auditory_hypersensitive"],
        "communication_support_tags": [],
        "contraindication_tags": [],
    },
    # La cohorte de la calibración. No se abren para mirarlas una a una: existen
    # para que los tramos de riesgo tengan días suficientes con los que
    # comprobarse. Ver `SUBJECT_COHORTE_C` en `ids`.
    {
        "subject_id": ids.SUBJECT_COHORTE_C,
        "tenant_id": ids.TENANT_A,
        "cohort_kind": "real_subject",
        "display_label": "Niña demo 7",
        "care_mode": "home_only",
        "sensory_profile_tags": [],
        "communication_support_tags": [],
        "contraindication_tags": [],
    },
    {
        "subject_id": ids.SUBJECT_COHORTE_D,
        "tenant_id": ids.TENANT_A,
        "cohort_kind": "real_subject",
        "display_label": "Niño demo 8",
        "care_mode": "home_and_therapy",
        "sensory_profile_tags": [],
        "communication_support_tags": [],
        "contraindication_tags": [],
    },
    {
        "subject_id": ids.SUBJECT_COHORTE_E,
        "tenant_id": ids.TENANT_A,
        "cohort_kind": "real_subject",
        "display_label": "Niña demo 9",
        "care_mode": "home_only",
        "sensory_profile_tags": [],
        "communication_support_tags": [],
        "contraindication_tags": [],
    },
    {
        "subject_id": ids.SUBJECT_COHORTE_F,
        "tenant_id": ids.TENANT_A,
        "cohort_kind": "real_subject",
        "display_label": "Niño demo 10",
        "care_mode": "home_and_therapy",
        "sensory_profile_tags": [],
        "communication_support_tags": [],
        "contraindication_tags": [],
    },
    {
        "subject_id": ids.SUBJECT_COHORTE_G,
        "tenant_id": ids.TENANT_A,
        "cohort_kind": "real_subject",
        "display_label": "Niña demo 11",
        "care_mode": "home_only",
        "sensory_profile_tags": [],
        "communication_support_tags": [],
        "contraindication_tags": [],
    },
    {
        "subject_id": ids.SUBJECT_COHORTE_H,
        "tenant_id": ids.TENANT_A,
        "cohort_kind": "real_subject",
        "display_label": "Niño demo 12",
        "care_mode": "home_and_therapy",
        "sensory_profile_tags": [],
        "communication_support_tags": [],
        "contraindication_tags": [],
    },
    {
        "subject_id": ids.SUBJECT_TENANT_B,
        "cohort_kind": "demo_fixture",
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
    (ids.CAREGIVER_A, ids.SUBJECT_REAL, CAREGIVER_CAPABILITIES),
    (ids.CAREGIVER_A, ids.SUBJECT_REAL_B, CAREGIVER_CAPABILITIES),
    (ids.CAREGIVER_A, ids.SUBJECT_SUENO, CAREGIVER_CAPABILITIES),
    (ids.CAREGIVER_A, ids.SUBJECT_COHORTE_C, CAREGIVER_CAPABILITIES),
    (ids.CAREGIVER_A, ids.SUBJECT_COHORTE_D, CAREGIVER_CAPABILITIES),
    (ids.CAREGIVER_A, ids.SUBJECT_COHORTE_E, CAREGIVER_CAPABILITIES),
    (ids.CAREGIVER_A, ids.SUBJECT_COHORTE_F, CAREGIVER_CAPABILITIES),
    (ids.CAREGIVER_A, ids.SUBJECT_COHORTE_G, CAREGIVER_CAPABILITIES),
    (ids.CAREGIVER_A, ids.SUBJECT_COHORTE_H, CAREGIVER_CAPABILITIES),
    (ids.PROFESSIONAL_A, ids.SUBJECT_ANA, PROFESSIONAL_CAPABILITIES),
    (ids.PROFESSIONAL_A, ids.SUBJECT_BETO, PROFESSIONAL_CAPABILITIES),
    (ids.PROFESSIONAL_A, ids.SUBJECT_REAL, PROFESSIONAL_CAPABILITIES),
    (ids.PROFESSIONAL_A, ids.SUBJECT_REAL_B, PROFESSIONAL_CAPABILITIES),
    (ids.PROFESSIONAL_A, ids.SUBJECT_SUENO, PROFESSIONAL_CAPABILITIES),
    (ids.PROFESSIONAL_A, ids.SUBJECT_COHORTE_C, PROFESSIONAL_CAPABILITIES),
    (ids.PROFESSIONAL_A, ids.SUBJECT_COHORTE_D, PROFESSIONAL_CAPABILITIES),
    (ids.PROFESSIONAL_A, ids.SUBJECT_COHORTE_E, PROFESSIONAL_CAPABILITIES),
    (ids.PROFESSIONAL_A, ids.SUBJECT_COHORTE_F, PROFESSIONAL_CAPABILITIES),
    (ids.PROFESSIONAL_A, ids.SUBJECT_COHORTE_G, PROFESSIONAL_CAPABILITIES),
    (ids.PROFESSIONAL_A, ids.SUBJECT_COHORTE_H, PROFESSIONAL_CAPABILITIES),
    (ids.UNACCREDITED_PROFESSIONAL_A, ids.SUBJECT_ANA, PROFESSIONAL_CAPABILITIES),
    (ids.CAREGIVER_B, ids.SUBJECT_TENANT_B, CAREGIVER_CAPABILITIES),
    (ids.PROFESSIONAL_B, ids.SUBJECT_TENANT_B, PROFESSIONAL_CAPABILITIES),
)

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

TARGET_TENANT_A = {
    **{key: value for key, value in TARGET_DEMO.items() if key != "scope"},
    "target_definition_version": ids.TARGET_TENANT_A,
    "scope": "tenant",
    "tenant_id": ids.TENANT_A,
}

FIXTURE_DOCUMENT = {
    "source_id": "fixture-doc-001",
    "publisher": "FIXTURE_DEMO",
    "title": "Documento ficticio de demostración sobre rutinas y sueño",
    "document_version": "1.0.0",
    "publication_date": "2026-01-15",
    "canonical_url": "https://example.invalid/blubathon/fixture-doc-001/v1",
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
    # Los dos de arriba son los que citan las estrategias sembradas, por su
    # índice: no se reordenan ni se insertan otros antes. Lo que sigue solo se
    # añade al final.
    #
    # Estos fragmentos existen para que la recuperación tenga con qué casar.
    # `query_for()` arma la consulta con las etiquetas del catálogo —"Calidad
    # del sueño : Interrumpido", "Regulación general del día : Desregulación
    # frecuente"—, así que un corpus que no repita ese vocabulario deja al
    # sistema abstenido en `no_indexed_match` y no se puede probar nada.
    #
    # Son ficticios y lo dicen. No son guía clínica: el texto es deliberadamente
    # genérico y no prescribe nada que alguien pudiera aplicar creyendo que
    # viene de una fuente revisada.
    {
        "locator": "sección 2, párrafo 7",
        "text": (
            "Ante despertares nocturnos repetidos o pocas horas de sueño, la "
            "primera revisión es del entorno y de los horarios, no del "
            "comportamiento del día siguiente."
        ),
    },
    {
        "locator": "sección 3, párrafo 2",
        "text": (
            "Un despertar irritable o con llanto suele pedir un inicio de "
            "jornada más lento, con menos demandas en la primera hora."
        ),
    },
    {
        "locator": "sección 3, párrafo 5",
        "text": (
            "Cuando la persona despierta cansada o con sueño, conviene reservar "
            "las actividades que exigen más atención para más tarde."
        ),
    },
    {
        "locator": "sección 5, párrafo 1",
        "text": (
            "En un día con desregulación frecuente, reducir el número de "
            "transiciones ayuda más que insistir en completar lo planificado."
        ),
    },
    {
        "locator": "sección 5, párrafo 4",
        "text": (
            "La regulación general del día mejora cuando el apoyo llega antes "
            "del episodio y no como respuesta a él."
        ),
    },
    {
        "locator": "sección 6, párrafo 2",
        "text": (
            "El malestar gastrointestinal, incluidos el estreñimiento y la "
            "diarrea, puede explicar cambios de conducta que parecen sin causa."
        ),
    },
    {
        "locator": "sección 7, párrafo 1",
        "text": (
            "Si la medicación no se tomó, conviene registrarlo antes de "
            "atribuir el día a otros factores."
        ),
    },
    {
        "locator": "sección 8, párrafo 3",
        "text": (
            "Los cambios en la rutina se toleran mejor cuando se anuncian con "
            "antelación y se mantiene fijo algún punto del día."
        ),
    },
    {
        "locator": "sección 9, párrafo 2",
        "text": (
            "Frente a cambios en la alimentación, ofrecer opciones conocidas "
            "junto a la nueva reduce el rechazo sin forzar la situación."
        ),
    },
    {
        "locator": "sección 10, párrafo 1",
        "text": (
            "La participación en actividades y las interacciones sociales "
            "bajan cuando el día empezó mal; conviene ajustar la exigencia "
            "antes que retirarlas."
        ),
    },
    {
        "locator": "sección 11, párrafo 4",
        "text": (
            "Un nivel de alerta bajo durante la mañana pide revisar el "
            "descanso de la noche anterior antes que aumentar los estímulos."
        ),
    },
    {
        "locator": "sección 12, párrafo 1",
        "text": (
            "En un día tranquilo y con sueño reparador, mantener la rutina "
            "habitual es preferible a introducir novedades."
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
