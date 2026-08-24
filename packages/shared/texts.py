"""Frozen Spanish UI copy shared by API and web clients."""

FILTER_QUESTION_ES = "¿Hoy pasó algo distinto o fuera de lo común?"
INSUFFICIENT_DATA_TEMPLATE_ES = (
    "Todavía no tengo información suficiente para darte una estimación confiable. "
    "Me ayudaría saber: {variables}."
)

ERROR_MESSAGES_ES = {
    "faro_error": "No fue posible completar la solicitud.",
    "insufficient_data": "No hay información suficiente para completar este cálculo.",
    "contract_violation": "Los datos no cumplen el contrato esperado.",
    "model_not_ready": "El modelo todavía no está disponible.",
    "provenance_conflict": "La procedencia indicada no puede asignar un valor al campo.",
    "validation_error": "La solicitud contiene datos inválidos.",
    "not_found": "No se encontró el recurso solicitado.",
    "method_not_allowed": "El método solicitado no está disponible para esta ruta.",
    "http_error": "No fue posible procesar la solicitud HTTP.",
    "internal_error": "Ocurrió un error interno al procesar la solicitud.",
}

VARIABLE_LABELS_ES = {
    "sleep_hours": "horas de sueño",
    "sleep_quality": "calidad del sueño",
    "night_awakenings": "despertares nocturnos",
    "wake_state": "estado al despertar",
    "morning_support_need": "apoyo matinal",
    "gi_status": "salud digestiva",
    "food_changes": "cambios en alimentación",
    "routine_changes": "cambios de rutina",
    "alertness": "estado de alerta",
    "dysregulation_events": "desregulaciones del día",
    "activity_participation": "participación en actividades",
    "social_interactions": "interacciones sociales",
    "eating_status": "alimentación",
    "relevant_event_flag": "evento relevante",
    "medication_adherence": "adherencia a medicación",
}

VARIABLE_PROMPTS_ES = {
    "sleep_hours": "¿Cuántas horas durmió anoche?",
    "sleep_quality": "¿Cómo durmió anoche?",
    "night_awakenings": "¿Cuántas veces se despertó en la noche?",
    "wake_state": "¿Cómo despertó hoy?",
    "morning_support_need": "¿Cuánto apoyo necesitó para iniciar el día?",
    "gi_status": "¿Tuvo molestias digestivas hoy?",
    "routine_changes": "¿Hubo algún cambio en su rutina?",
    "alertness": "¿Cómo estuvo su estado de alerta hoy?",
    "social_interactions": "¿Cómo fueron sus interacciones sociales?",
    "activity_participation": "¿Cómo participó en sus actividades?",
    "eating_status": "¿Cómo estuvo su alimentación hoy?",
    "food_changes": "¿Hubo cambios en lo que comió?",
    "dysregulation_events": "¿Tuvo episodios de desregulación hoy? ¿Cuántos?",
    "relevant_event_flag": FILTER_QUESTION_ES,
    "medication_adherence": "¿Tomó su medicación hoy?",
}

ORDINAL_ANCHORS_ES = {
    "sleep_quality": {
        1: "Pésima — casi no durmió",
        2: "Dificultad de conciliación — le costó quedarse dormido",
        3: "Interrumpido — durmió, pero con despertares",
        4: "Buena — durmió bien, alguna interrupción menor",
        5: "Reparador — durmió de corrido y despertó descansado",
    },
    "wake_state": {
        1: "Irritable / llorando — despertó alterado",
        2: "Molesto — despertó sensible o a la defensiva",
        3: "Cansado / con sueño — despertó sin energía",
        4: "Tranquilo — despertó bien, con buena disposición",
        5: "Tranquilo / alegre — despertó descansado y regulado",
    },
    "morning_support_need": {
        1: "Autónomo — hizo su rutina solo",
        2: "Poco apoyo — recordatorios puntuales",
        3: "Apoyo moderado — acompañamiento en varias partes",
        4: "Mucho apoyo — hubo que guiar casi todo",
        5: "Apoyo total — no logró iniciar el día sin ayuda constante",
    },
    "gi_status": {
        1: "Muy mal — dolor evidente o vómitos",
        2: "Diarrea — deposiciones sueltas o dolor abdominal",
        3: "Estreñimiento — cuesta o lleva días sin ir",
        4: "Bien — sin molestias notorias",
        5: "Normal — digestión normal, sin señales",
    },
    "alertness": {
        1: "Bajo (letárgico) — somnoliento, sin energía",
        2: "Calmado — más lento o replegado de lo habitual",
        3: "Óptimo (regulado) — alerta y disponible",
        4: "Activado — más inquieto de lo habitual",
        5: "Alto (sobreexcitado) — muy activado, difícil de calmar",
    },
    "activity_participation": {
        1: "No participó",
        2: "Participó muy poco, con mucha resistencia",
        3: "Participó a ratos",
        4: "Participó bien la mayor parte del tiempo",
        5: "Participó plenamente",
    },
    "social_interactions": {
        1: "Muy difíciles — conflictos o retraimiento marcado",
        2: "Difíciles — le costó relacionarse",
        3: "Neutras — sin nada destacable",
        4: "Buenas — interactuó bien",
        5: "Muy buenas — disfrutó el contacto con otros",
    },
    "eating_status": {
        1: "Casi no comió",
        2: "Comió poco o rechazó comidas",
        3: "Comió algo menos de lo habitual",
        4: "Comió bien",
        5: "Comió muy bien, sin dificultad",
    },
}

MEDICATION_ADHERENCE_ANCHORS_ES = {
    "taken": "Sí — la tomó como corresponde",
    "missed": "No — hoy no la tomó",
    "not_applicable": "No aplica — no tiene medicación indicada",
}

BAND_LABELS_ES = {
    "verde": "riesgo bajo",
    "ambar": "riesgo medio",
    "rojo": "riesgo alto",
}

CLOSING_QUESTION_TEMPLATE_ES = (
    "¿El {target_date} hubo una crisis o episodio de desregulación mayor?"
)
