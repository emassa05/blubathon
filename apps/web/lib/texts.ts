/**
 * Textos visibles en español de Chile.
 *
 * PROVISIONAL - PUERTO HACIA P1. `CONVENTIONS 10` sitúa los textos normativos en
 * `packages/shared/texts.py`, y P1 genera desde ahí los textos de TypeScript.
 * Mientras eso no exista, la UI los toma de aquí; el reemplazo es cambiar este
 * único archivo por el módulo generado.
 */

export const TEXTS = {
  appName: "Faro",
  tagline: "Registro diario, estadística personal y apoyo revisado",
  emergencyTitle: "Faro no monitorea emergencias",
  emergencyBody:
    "Faro no te avisará si algo urgente ocurre. Ante peligro inmediato sigue de " +
    "inmediato los protocolos de emergencia o resguardo de tu comunidad; no esperes " +
    "una alerta de esta aplicación.",
  loading: "Cargando…",
  empty: "No hay nada que mostrar todavía.",
  errorTitle: "No pudimos completar la operación",
  retry: "Reintentar",
  abstainedTitle: "Faro se abstiene",
  abstainedBody:
    "No hay información suficiente para estimar esto. Una abstención no es un error " +
    "ni significa que todo esté bien.",
  conflictedTitle: "Reportes incompatibles",
  conflictedBody:
    "Existen reportes que se contradicen para esta ventana. El caso queda marcado " +
    "como conflicto y no se usa para estadística.",
  expiredTitle: "La ventana de captura ya cerró",
  expiredBody:
    "Puedes registrar lo que recuerdes, pero quedará como reporte tardío y no entra " +
    "al conjunto principal.",
  suggestionBadge: "Sugerencia",
  suggestionHelp:
    "Esto es una sugerencia basada en tu propio historial. Si no la tocas, no se guarda nada.",
  suggestionAccept: "Usar esta sugerencia",
  suggestionEdit: "Escribir otro valor",
  unknownAnswer: "No sé",
  simulationBadge: "Simulación",
  simulationHelp:
    "Este número viene de una simulación diseñada, no de datos de una persona real. " +
    "No es una probabilidad clínica.",
  awaitingReviewTitle: "Esperando revisión profesional",
  awaitingReviewBody:
    "Estas sugerencias todavía no están aprobadas. No hay nada que aplicar aún.",
  pendingOutcomeTitle: "Resultado pendiente",
  submit: "Enviar el registro del día",
  submitted: "Registro enviado",
  queueTitle: "Todos los campos",
  highlightedTitle: "Lo más útil de hoy",
  inboxTitle: "Recomendaciones por revisar",
  scenarioTitle: "Escenario mínimo",
  citationsTitle: "Citas verificables",
  historyTitle: "Historial de versiones",
  approve: "Aprobar",
  reject: "Rechazar",
  substitute: "Sustituir con plan propio",
  defer: "Diferir",
  notApplicable: "No aplica",
  recordExecution: "Registrar aplicación",
  applied: "Se aplicó",
  notApplied: "No se aplicó",
  unknownApplication: "No se sabe",
} as const;

export const OUTCOME_REQUEST_STATUS_ES: Record<string, string> = {
  open: "Esperando tu respuesta",
  reported: "Respondido",
  conflicted: "Con reportes incompatibles",
  missing: "Sin respuesta dentro del plazo",
};

export const RESOLUTION_STATUS_ES: Record<string, string> = {
  pending: "Sin resolver",
  yes: "Ocurrió",
  no: "No ocurrió",
  unknown: "No se pudo saber",
  conflicted: "En conflicto",
};

export const REVIEW_STATUS_ES: Record<string, string> = {
  pending: "Sin revisar",
  approved: "Aprobada",
  rejected: "Rechazada",
  human_plan_substituted: "Sustituida por un plan propio",
  not_applicable: "No aplica",
  deferred: "Diferida",
};

export const ABSTENTION_REASONS_ES: Record<string, string> = {
  insufficient_verified_outcomes:
    "Aún no hay suficientes resultados verificados de esta persona.",
  care_mode_history_unavailable: "Falta el modo de cuidado histórico del episodio.",
  unresolved_conflict: "Hay un conflicto sin resolver en la ventana usada.",
  not_trainable_single_class: "El modelo no es entrenable con una sola clase observada.",
  real_subject_rejected_by_simulation_track:
    "El modelo de simulación no se aplica a personas reales.",
  simulation_fixture_unavailable: "No hay un escenario de simulación para esta persona.",
  corpus_not_ready: "Todavía no hay un corpus autorizado y versionado.",
  clinical_review_unavailable: "Falta una revisión clínica autorizada.",
  catalog_suspended: "Una dependencia del catálogo está suspendida.",
  catalog_ambiguous: "Hay más de un catálogo activo vigente.",
  catalog_not_ready: "No hay un catálogo activo para esta organización.",
  no_approved_match: "Ninguna estrategia aprobada calza con este escenario.",
  scenario_unavailable_conflict: "El escenario tiene valores en conflicto.",
  scenario_unavailable_profile: "Falta el perfil versionado de la persona.",
  catalog_scope_mismatch: "El catálogo consultado no pertenece a esta organización.",
  target_definition_unavailable:
    "No hay una definición de objetivo activa para registrar resultados reales.",
  target_definition_ambiguous:
    "Hay más de una definición de objetivo vigente; el sistema no elige por su cuenta.",
};

export const FIELD_LABELS_ES: Record<string, string> = {
  sleep_hours: "Horas de sueño",
  sleep_quality: "Calidad del sueño",
  night_awakenings: "Despertares nocturnos",
  wake_state: "Cómo despertó",
  morning_support_need: "Apoyo necesario en la mañana",
  gi_status: "Estado digestivo",
  medication_adherence: "Medicación",
  food_changes: "Cambios en la alimentación",
  routine_changes: "Cambios en la rutina",
  alertness: "Nivel de activación",
  dysregulation_event_count: "Episodios de desregulación observados",
  daily_regulation_state: "Regulación durante el día",
  activity_participation: "Participación en actividades",
  social_interactions: "Interacciones sociales",
  eating_status: "Alimentación",
  attendance_status: "Asistencia",
  relevant_event_flag: "¿Pasó algo distinto hoy?",
  behavior_tags: "Conductas observadas",
  notes: "Notas",
};

export const ENUM_LABELS_ES: Record<string, Record<string, string>> = {
  sleep_quality: {
    restorative: "Reparador",
    interrupted: "Interrumpido",
    sleep_onset_difficulty: "Costó quedarse dormido/a",
    other: "Otro",
  },
  wake_state: {
    calm_happy: "Tranquilo/a y contento/a",
    tired_sleepy: "Cansado/a o con sueño",
    irritable_crying: "Irritable o llorando",
    other: "Otro",
  },
  gi_status: {
    normal: "Normal",
    constipation: "Estreñimiento",
    diarrhea: "Diarrea",
    other: "Otro",
  },
  medication_adherence: {
    taken: "La tomó",
    missed: "No la tomó",
    not_applicable: "No corresponde",
  },
  alertness: {
    low: "Baja",
    calm: "Calmada",
    optimal: "Óptima",
    high: "Alta",
    other: "Otra",
  },
  daily_regulation_state: {
    excellent: "Muy bien",
    stable_with_support: "Estable con apoyo",
    frequent_dysregulation: "Desregulación frecuente",
    other: "Otro",
  },
  attendance_status: {
    present: "Asistió",
    absent: "No asistió",
    not_applicable: "No corresponde",
  },
  behavior_tags: {
    self_regulation_attempt: "Intento de autorregulación",
    sensory_seeking: "Búsqueda sensorial",
    sensory_avoiding: "Evitación sensorial",
    communication_attempt: "Intento de comunicación",
    routine_disruption: "Ruptura de rutina",
    other: "Otra",
  },
};

export const ORDINAL_ANCHORS_ES: Record<string, string[]> = {
  morning_support_need: [
    "Sin apoyo",
    "Apoyo puntual",
    "Apoyo moderado",
    "Apoyo constante",
    "Apoyo total",
  ],
  activity_participation: ["Nada", "Poco", "Parcial", "Casi todo", "Todo"],
  social_interactions: ["Ninguna", "Pocas", "Algunas", "Varias", "Muchas"],
  eating_status: ["Casi nada", "Poco", "Lo habitual", "Bastante", "Todo"],
};

export function fieldLabel(fieldCode: string): string {
  return FIELD_LABELS_ES[fieldCode] ?? fieldCode;
}

export function optionLabel(fieldCode: string, value: string): string {
  return ENUM_LABELS_ES[fieldCode]?.[value] ?? value;
}

export function abstentionReason(code: string): string {
  return ABSTENTION_REASONS_ES[code] ?? code;
}
