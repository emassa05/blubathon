/**
 * Textos visibles en español de Chile.
 *
 * La copia normativa vive en `packages/shared/texts.py` y llega generada en
 * `FARO_TEXTS_ES` (`CONVENTIONS 10`, H1). Este módulo no la reescribe: la mapea
 * a los nombres que usan los componentes y añade únicamente el rótulo de
 * interfaz -títulos de sección, verbos de botón- que no es contrato clínico.
 */

import { FARO_TEXTS_ES } from "@faro/contract";

export const TEXTS = {
  // Rótulos de la aplicación: no son texto normativo.
  appName: "Faro",
  tagline: "Registro diario, estadística personal y apoyo revisado",
  emergencyTitle: "Faro no monitorea emergencias",
  errorTitle: "No pudimos completar la operación",
  retry: "Reintentar",
  abstainedTitle: "Faro se abstiene",
  // `CONVENTIONS 14` exige que una abstención no se presente como error. P1
  // publica la copia de cada razón, no este encuadre, así que vive aquí.
  abstainedBody:
    "No hay información suficiente para estimar esto. Una abstención no es un error " +
    "ni significa que todo esté bien.",
  conflictedTitle: "Reportes incompatibles",
  expiredTitle: "La ventana de captura ya cerró",
  suggestionBadge: "Sugerencia",
  suggestionAccept: "Usar esta sugerencia",
  suggestionEdit: "Escribir otro valor",
  simulationBadge: "Simulación",
  awaitingReviewTitle: "Esperando revisión profesional",
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
  tagCatalogueUnpublished:
    "El catálogo de conductas todavía no está publicado, así que este campo no " +
    "ofrece opciones. No inventamos categorías clínicas.",

  // Copia normativa: viene del contrato, no de este archivo.
  emergencyBody: FARO_TEXTS_ES.emergencyLimitEs,
  intendedUse: FARO_TEXTS_ES.intendedUseEs,
  loading: FARO_TEXTS_ES.loadingEs,
  empty: FARO_TEXTS_ES.emptyEs,
  errorBody: FARO_TEXTS_ES.genericErrorEs,
  conflictedBody: FARO_TEXTS_ES.conflictedStateEs,
  expiredBody: FARO_TEXTS_ES.expiredSessionEs,
  suggestionHelp: FARO_TEXTS_ES.defaultSuggestionHintEs,
  auditSessionHint: FARO_TEXTS_ES.auditSessionHintEs,
  unknownAnswer: FARO_TEXTS_ES.unknownAnswerEs,
  unknownAnswerHint: FARO_TEXTS_ES.unknownAnswerHintEs,
  simulationHelp: FARO_TEXTS_ES.simulationDisclaimerEs,
  awaitingReviewBody: FARO_TEXTS_ES.awaitingProfessionalReviewEs,
  filterNegativeHint: FARO_TEXTS_ES.filterNegativeHintEs,
} as const;

/**
 * `SPEC 4.4` no publica rótulos para el estado derivado de la solicitud, así que
 * este mapa es de interfaz. Los estados de resolución sí son contrato.
 */
export const OUTCOME_REQUEST_STATUS_ES: Record<string, string> = {
  open: "Esperando tu respuesta",
  reported: "Respondido",
  conflicted: "Con reportes incompatibles",
  missing: "Sin respuesta dentro del plazo",
};

export const RESOLUTION_STATUS_ES: Record<string, string> =
  FARO_TEXTS_ES.outcomeResolutionLabelsEs;

/** Rótulos de decisión de revisión; `SPEC 10.2` no publica su copia visible. */
export const REVIEW_STATUS_ES: Record<string, string> = {
  pending: "Sin revisar",
  approved: "Aprobada",
  rejected: "Rechazada",
  human_plan_substituted: "Sustituida por un plan propio",
  not_applicable: "No aplica",
  deferred: "Diferida",
};

const ABSTENTION_REASONS_ES: Record<string, string> = {
  ...FARO_TEXTS_ES.predictionAbstentionEs,
  ...FARO_TEXTS_ES.recommendationAbstentionEs,
};

export const FIELD_LABELS_ES: Record<string, string> = FARO_TEXTS_ES.fieldLabelsEs;

const ENUM_LABELS_ES: Record<string, Record<string, string>> = {
  sleep_quality: FARO_TEXTS_ES.sleepQualityLabelsEs,
  wake_state: FARO_TEXTS_ES.wakeStateLabelsEs,
  gi_status: FARO_TEXTS_ES.giStatusLabelsEs,
  medication_adherence: FARO_TEXTS_ES.medicationAdherenceLabelsEs,
  alertness: FARO_TEXTS_ES.alertnessLabelsEs,
  daily_regulation_state: FARO_TEXTS_ES.dailyRegulationLabelsEs,
  attendance_status: FARO_TEXTS_ES.attendanceLabelsEs,
};

export const ORDINAL_ANCHORS_ES: Record<string, readonly string[]> =
  FARO_TEXTS_ES.ordinalAnchorsEs;

export function fieldLabel(fieldCode: string): string {
  return FIELD_LABELS_ES[fieldCode] ?? fieldCode;
}

export function optionLabel(fieldCode: string, value: string): string {
  return ENUM_LABELS_ES[fieldCode]?.[value] ?? value;
}

/**
 * Una razón sin copia publicada se muestra tal cual: el catálogo cerrado de
 * `SPEC 8.5` y `SPEC 9.6` es de P1 y aquí no se completa a mano.
 */
export function abstentionReason(code: string): string {
  return ABSTENTION_REASONS_ES[code] ?? code;
}
