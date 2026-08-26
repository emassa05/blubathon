/** Tipos del dominio de la pantalla Salud. Nombres de dominio en español. */

export type IconoFactor = "luna" | "rombo";

/**
 * El diseño solo especifica la etiqueta "Alta prioridad". El tipo queda abierto
 * a más niveles sin tocar la UI: basta añadir la clave aquí y en
 * `ETIQUETA_PRIORIDAD`.
 */
export type PrioridadFactor = "alta";

export interface FactorRiesgo {
  readonly id: string;
  readonly icono: IconoFactor;
  readonly titulo: string;
  readonly detalle: string;
  readonly prioridad: PrioridadFactor;
}

export type EstadoFormulario = "respondido" | "sin-responder";

export interface RegistroFormulario {
  readonly id: string;
  readonly dia: string;
  readonly estado: EstadoFormulario;
}

export interface Recomendacion {
  readonly texto: string;
}

/** Lo que la pantalla necesita saber de un día. Es el contrato con la API. */
export interface ResumenSalud {
  /** Fecha ISO 8601 (YYYY-MM-DD) del día que abre la pantalla. */
  readonly fecha: string;
  /** Riesgo de desregulación del día, 0-100. Elige la ilustración de cabecera. */
  readonly riesgo: number;
  /** Confianza del modelo en ese riesgo, 0-100. */
  readonly confianza: number;
  readonly recomendacion: Recomendacion;
  readonly factores: readonly FactorRiesgo[];
  readonly formularios: readonly RegistroFormulario[];
  readonly formularioPendiente: boolean;
}

/* Vocabulario visible. Vive junto al tipo para que añadir un valor obligue a
   dar su etiqueta. */

export const ETIQUETA_PRIORIDAD: Record<PrioridadFactor, string> = {
  alta: "Alta prioridad",
};

export const ETIQUETA_ESTADO_FORMULARIO: Record<EstadoFormulario, string> = {
  respondido: "Respondido",
  "sin-responder": "Sin responder",
};
