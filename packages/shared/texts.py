"""Spanish (Chile) copy shared by the API and every client.

Visible text lives here or in the versioned catalogue, never inline in a
component (CONVENTIONS 10). The language is affirmative and non-diagnostic, an
abstention is never presented as an error, and the emergency limit of SPEC 13.2
is available for every screen that needs it.
"""

from __future__ import annotations

from types import MappingProxyType

from packages.shared.enums import (
    Alertness,
    AttendanceStatus,
    DailyRegulationState,
    ErrorCode,
    FieldCode,
    GiStatus,
    MedicationAdherence,
    OutcomeReportValue,
    OutcomeResolutionStatus,
    PredictionAbstentionReason,
    RecommendationAbstentionReason,
    SleepQuality,
    Source,
    WakeState,
)

# SPEC 13.2 and CONVENTIONS 14: shown on entry, abstention, results and
# recommendations. Faro is not emergency monitoring and must never delay a local
# urgent or safeguarding protocol.
EMERGENCY_LIMIT_ES = (
    "Faro no vigila emergencias ni envía alertas. Ante peligro inmediato, sigue de inmediato "
    "los protocolos de emergencia o resguardo de tu localidad."
)

INTENDED_USE_ES = (
    "Faro organiza registros, calcula estadísticas personales y muestra estimaciones "
    "experimentales. No diagnostica, no indica tratamientos y no reemplaza el criterio "
    "profesional."
)

SIMULATION_DISCLAIMER_ES = (
    "Este número viene de una simulación diseñada por el equipo, no de datos de una persona "
    "real. No es una probabilidad clínica."
)

DEFAULT_SUGGESTION_HINT_ES = (
    "Sugerencia basada en tu historial. El campo sigue vacío hasta que la toques o escribas "
    "otro valor."
)

AUDIT_SESSION_HINT_ES = (
    "Hoy el formulario no muestra sugerencias. Así podemos comparar respuestas con y sin ayuda."
)

FILTER_QUESTION_ES = "¿Hoy pasó algo distinto o fuera de lo común?"

FILTER_NEGATIVE_HINT_ES = (
    'Responder "no" solo guarda esa respuesta. No completa ningún otro campo por ti.'
)

UNKNOWN_ANSWER_ES = "No sé"
UNKNOWN_ANSWER_HINT_ES = 'Se guarda como "no sé", que no es lo mismo que un cero ni que un no.'

AWAITING_PROFESSIONAL_REVIEW_ES = (
    "Hay sugerencias esperando revisión profesional. Todavía no se muestran."
)

FIELD_LABELS_ES: MappingProxyType[FieldCode, str] = MappingProxyType(
    {
        FieldCode.SLEEP_HOURS: "Horas de sueño",
        FieldCode.SLEEP_QUALITY: "Calidad del sueño",
        FieldCode.NIGHT_AWAKENINGS: "Despertares nocturnos",
        FieldCode.WAKE_STATE: "Cómo despertó",
        FieldCode.MORNING_SUPPORT_NEED: "Apoyo necesario en la mañana",
        FieldCode.GI_STATUS: "Estado gastrointestinal",
        FieldCode.MEDICATION_ADHERENCE: "Medicación",
        FieldCode.FOOD_CHANGES: "Cambios en la alimentación",
        FieldCode.ROUTINE_CHANGES: "Cambios en la rutina",
        FieldCode.ALERTNESS: "Nivel de alerta",
        FieldCode.DYSREGULATION_EVENT_COUNT: "Episodios de desregulación observados",
        FieldCode.DAILY_REGULATION_STATE: "Regulación general del día",
        FieldCode.ACTIVITY_PARTICIPATION: "Participación en actividades",
        FieldCode.SOCIAL_INTERACTIONS: "Interacciones sociales",
        FieldCode.EATING_STATUS: "Alimentación",
        FieldCode.ATTENDANCE_STATUS: "Asistencia",
        FieldCode.RELEVANT_EVENT_FLAG: "Ocurrió algo relevante",
        FieldCode.BEHAVIOR_TAGS: "Conductas observadas",
        FieldCode.NOTES: "Notas",
    }
)

FIELD_PROMPTS_ES: MappingProxyType[FieldCode, str] = MappingProxyType(
    {
        FieldCode.SLEEP_HOURS: "¿Cuántas horas durmió anoche?",
        FieldCode.SLEEP_QUALITY: "¿Cómo fue el sueño de anoche?",
        FieldCode.NIGHT_AWAKENINGS: "¿Cuántas veces despertó durante la noche?",
        FieldCode.WAKE_STATE: "¿Cómo despertó esta mañana?",
        FieldCode.MORNING_SUPPORT_NEED: "¿Cuánto apoyo necesitó en la mañana?",
        FieldCode.GI_STATUS: "¿Cómo estuvo su estado gastrointestinal?",
        FieldCode.MEDICATION_ADHERENCE: "¿Tomó la medicación indicada?",
        FieldCode.FOOD_CHANGES: "¿Hubo cambios en la alimentación?",
        FieldCode.ROUTINE_CHANGES: "¿Hubo cambios en la rutina?",
        FieldCode.ALERTNESS: "¿Cómo estuvo su nivel de alerta?",
        FieldCode.DYSREGULATION_EVENT_COUNT: "¿Cuántos episodios de desregulación observaste?",
        FieldCode.DAILY_REGULATION_STATE: "¿Cómo fue la regulación durante el día?",
        FieldCode.ACTIVITY_PARTICIPATION: "¿Cómo participó en las actividades?",
        FieldCode.SOCIAL_INTERACTIONS: "¿Cómo fueron sus interacciones con otras personas?",
        FieldCode.EATING_STATUS: "¿Cómo fue su alimentación hoy?",
        FieldCode.ATTENDANCE_STATUS: "¿Asistió hoy?",
        FieldCode.RELEVANT_EVENT_FLAG: FILTER_QUESTION_ES,
        FieldCode.BEHAVIOR_TAGS: "¿Qué conductas observaste hoy?",
        FieldCode.NOTES: "¿Quieres agregar alguna nota?",
    }
)

# Anchors stay visible in the UI. The estimator never averages these categories
# and never assumes the distance between 1 and 2 equals the one between 4 and 5.
ORDINAL_ANCHORS_ES: MappingProxyType[FieldCode, tuple[str, ...]] = MappingProxyType(
    {
        FieldCode.MORNING_SUPPORT_NEED: (
            "1 - Sin apoyo",
            "2 - Apoyo puntual",
            "3 - Apoyo moderado",
            "4 - Apoyo frecuente",
            "5 - Apoyo constante",
        ),
        FieldCode.ACTIVITY_PARTICIPATION: (
            "1 - No participó",
            "2 - Participó muy poco",
            "3 - Participó a ratos",
            "4 - Participó casi todo el tiempo",
            "5 - Participó de principio a fin",
        ),
        FieldCode.SOCIAL_INTERACTIONS: (
            "1 - Sin interacción",
            "2 - Interacción muy breve",
            "3 - Alguna interacción",
            "4 - Interacción frecuente",
            "5 - Interacción sostenida",
        ),
        FieldCode.EATING_STATUS: (
            "1 - No comió",
            "2 - Comió muy poco",
            "3 - Comió menos de lo habitual",
            "4 - Comió como habitualmente",
            "5 - Comió más de lo habitual",
        ),
    }
)

SOURCE_LABELS_ES: MappingProxyType[Source, str] = MappingProxyType(
    {
        Source.HOME: "Casa",
        Source.THERAPY: "Terapia",
        Source.SCHOOL: "Colegio",
    }
)

SLEEP_QUALITY_LABELS_ES: MappingProxyType[SleepQuality, str] = MappingProxyType(
    {
        SleepQuality.RESTORATIVE: "Reparador",
        SleepQuality.INTERRUPTED: "Interrumpido",
        SleepQuality.SLEEP_ONSET_DIFFICULTY: "Costó quedarse dormido",
        SleepQuality.OTHER: "Otro",
    }
)

WAKE_STATE_LABELS_ES: MappingProxyType[WakeState, str] = MappingProxyType(
    {
        WakeState.CALM_HAPPY: "Tranquilo o contento",
        WakeState.TIRED_SLEEPY: "Cansado o con sueño",
        WakeState.IRRITABLE_CRYING: "Irritable o llorando",
        WakeState.OTHER: "Otro",
    }
)

GI_STATUS_LABELS_ES: MappingProxyType[GiStatus, str] = MappingProxyType(
    {
        GiStatus.NORMAL: "Normal",
        GiStatus.CONSTIPATION: "Estreñimiento",
        GiStatus.DIARRHEA: "Diarrea",
        GiStatus.OTHER: "Otro",
    }
)

MEDICATION_ADHERENCE_LABELS_ES: MappingProxyType[MedicationAdherence, str] = MappingProxyType(
    {
        MedicationAdherence.TAKEN: "La tomó",
        MedicationAdherence.MISSED: "No la tomó",
        MedicationAdherence.NOT_APPLICABLE: "No corresponde",
    }
)

ALERTNESS_LABELS_ES: MappingProxyType[Alertness, str] = MappingProxyType(
    {
        Alertness.LOW: "Bajo",
        Alertness.CALM: "Calmado",
        Alertness.OPTIMAL: "Óptimo",
        Alertness.HIGH: "Alto",
        Alertness.OTHER: "Otro",
    }
)

DAILY_REGULATION_LABELS_ES: MappingProxyType[DailyRegulationState, str] = MappingProxyType(
    {
        DailyRegulationState.EXCELLENT: "Excelente",
        DailyRegulationState.STABLE_WITH_SUPPORT: "Estable con apoyo",
        DailyRegulationState.FREQUENT_DYSREGULATION: "Desregulación frecuente",
        DailyRegulationState.OTHER: "Otro",
    }
)

ATTENDANCE_LABELS_ES: MappingProxyType[AttendanceStatus, str] = MappingProxyType(
    {
        AttendanceStatus.PRESENT: "Asistió",
        AttendanceStatus.ABSENT: "No asistió",
        AttendanceStatus.NOT_APPLICABLE: "No corresponde",
    }
)

OUTCOME_VALUE_LABELS_ES: MappingProxyType[OutcomeReportValue, str] = MappingProxyType(
    {
        OutcomeReportValue.YES: "Sí, ocurrió",
        OutcomeReportValue.NO: "No ocurrió",
        OutcomeReportValue.UNKNOWN: "No lo sé",
    }
)

OUTCOME_RESOLUTION_LABELS_ES: MappingProxyType[OutcomeResolutionStatus, str] = MappingProxyType(
    {
        OutcomeResolutionStatus.PENDING: "Esperando respuesta",
        OutcomeResolutionStatus.YES: "Ocurrió",
        OutcomeResolutionStatus.NO: "No ocurrió",
        OutcomeResolutionStatus.UNKNOWN: "Sin respuesta concluyente",
        OutcomeResolutionStatus.CONFLICTED: "Respuestas incompatibles",
    }
)

# An abstention is a valid answer, so its copy explains what is missing instead
# of apologising for an error.
PREDICTION_ABSTENTION_ES: MappingProxyType[PredictionAbstentionReason, str] = MappingProxyType(
    {
        PredictionAbstentionReason.COLLECTING_DATA: (
            "Todavía estamos reuniendo información para esta estimación."
        ),
        PredictionAbstentionReason.INSUFFICIENT_VERIFIED_OUTCOMES: (
            "Aún no hay suficientes resultados confirmados para estimar de forma honesta."
        ),
        PredictionAbstentionReason.UNRESOLVED_CONFLICT: (
            "Hay respuestas incompatibles sin resolver en el período considerado."
        ),
        PredictionAbstentionReason.CARE_MODE_HISTORY_UNAVAILABLE: (
            "Falta el modo de acompañamiento registrado para comparar con el historial."
        ),
        PredictionAbstentionReason.TARGET_DEFINITION_UNAVAILABLE: (
            "No hay una definición de resultado aprobada y vigente."
        ),
        PredictionAbstentionReason.TARGET_DEFINITION_AMBIGUOUS: (
            "Hay más de una definición de resultado vigente al mismo tiempo."
        ),
        PredictionAbstentionReason.MODEL_STATE_NOT_SHADOW: (
            "El modelo candidato no está habilitado para generar resultados."
        ),
        PredictionAbstentionReason.PREDICTOR_MISSING: (
            "Falta una de las respuestas que este modelo necesita."
        ),
        PredictionAbstentionReason.PERSONAL_PREDICTOR_HISTORY_INSUFFICIENT: (
            "No hay suficiente historial personal para calcular la desviación."
        ),
        PredictionAbstentionReason.FEATURE_CONFLICT: (
            "Hay dos registros activos incompatibles para el mismo día."
        ),
        PredictionAbstentionReason.UNSUPPORTED_MAPPING: (
            "La importación usa una equivalencia que no está aprobada."
        ),
        PredictionAbstentionReason.CALIBRATION_FAILURE: (
            "La calibración no pudo completarse con estos datos."
        ),
        PredictionAbstentionReason.COHORT_NOT_ELIGIBLE: (
            "Esta estimación no corresponde para esta cohorte."
        ),
    }
)

RECOMMENDATION_ABSTENTION_ES: MappingProxyType[RecommendationAbstentionReason, str] = (
    MappingProxyType(
        {
            RecommendationAbstentionReason.CORPUS_NOT_READY: (
                "Todavía no hay fuentes autorizadas para respaldar sugerencias."
            ),
            RecommendationAbstentionReason.CLINICAL_REVIEW_UNAVAILABLE: (
                "Falta la revisión clínica que autoriza publicar estas estrategias."
            ),
            RecommendationAbstentionReason.CATALOG_SUSPENDED: (
                "El catálogo está suspendido porque una de sus fuentes dejó de estar vigente."
            ),
            RecommendationAbstentionReason.CATALOG_AMBIGUOUS: (
                "Hay más de un catálogo vigente, así que no se elige ninguno."
            ),
            RecommendationAbstentionReason.CATALOG_NOT_READY: (
                "No hay un catálogo vigente para esta organización."
            ),
            RecommendationAbstentionReason.NO_APPROVED_MATCH: (
                "No hay una estrategia aprobada que corresponda a esta situación."
            ),
            RecommendationAbstentionReason.SCENARIO_UNAVAILABLE_CONFLICT: (
                "Hay registros incompatibles para hoy, así que no se arma el escenario."
            ),
        }
    )
)

ERROR_MESSAGES_ES: MappingProxyType[ErrorCode, str] = MappingProxyType(
    {
        ErrorCode.VALIDATION_ERROR: "La solicitud contiene datos que no cumplen el contrato.",
        ErrorCode.UNAUTHENTICATED: "Necesitas iniciar sesión para continuar.",
        ErrorCode.FORBIDDEN: "No tienes autorización vigente para esta operación.",
        ErrorCode.NOT_FOUND: "No se encontró el recurso solicitado.",
        ErrorCode.IDEMPOTENCY_CONFLICT: (
            "Esa clave de idempotencia ya se usó con un contenido distinto."
        ),
        ErrorCode.REVISION_CONFLICT: "El recurso cambió desde que lo cargaste.",
        ErrorCode.RECOMMENDATION_DEPENDENCY_SUSPENDED: (
            "Esta recomendación depende de una versión suspendida y no admite nuevas acciones."
        ),
        ErrorCode.UNMAPPED_SOURCE_VALUE: (
            "La importación trae un valor que no está en la tabla de equivalencias."
        ),
        ErrorCode.TARGET_DEFINITION_AMBIGUOUS: (
            "Hay más de una definición de resultado vigente al mismo tiempo."
        ),
        ErrorCode.ENTRY_MODE_NOT_DERIVABLE: ("No se puede determinar cómo se ingresó este dato."),
        ErrorCode.SYNTHETIC_ROW_IN_REAL_SNAPSHOT: (
            "Un registro sintético no puede entrar en un cálculo con datos reales."
        ),
        ErrorCode.REAL_SUBJECT_NOT_ALLOWED_IN_DEMO: (
            "El modo demostración no puede operar con personas reales."
        ),
        ErrorCode.INTERNAL_ERROR: "Ocurrió un error interno al procesar la solicitud.",
    }
)

LOADING_ES = "Cargando…"
EMPTY_ES = "Todavía no hay nada que mostrar."
GENERIC_ERROR_ES = "No fue posible completar la solicitud."
EXPIRED_SESSION_ES = "Esta sesión expiró. Puedes abrir una nueva."
CONFLICTED_STATE_ES = "Hay información incompatible. Un profesional puede revisarla."
