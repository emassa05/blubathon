/**
 * Tipos del panel del terapeuta. Nombres de dominio en español, igual que
 * `types/salud.ts`.
 *
 * La diferencia con la pantalla del cuidador no es de estilo sino de sujeto:
 * allí hay un niño y un día, aquí hay una cartera de niños y una serie. Lo que
 * el terapeuta necesita decidir es a quién mirar primero, y para eso hace falta
 * comparar, no contemplar una cifra.
 */

/** Un punto de la serie de riesgo: un día con lo que se estimó y lo que pasó. */
export interface PuntoRiesgo {
  /** Fecha ISO 8601 (YYYY-MM-DD). */
  readonly fecha: string;
  /**
   * Riesgo estimado ese día, 0-100.
   *
   * `null` es abstención: el modelo no tenía resultados verificados suficientes.
   * La línea se corta ahí en vez de unir los dos extremos, porque un segmento
   * recto sobre un hueco afirma una progresión que nadie estimó.
   */
  readonly riesgo: number | null;
  /** Extremos del intervalo, 0-100, o `null` si el track no publica ninguno. */
  readonly banda: readonly [number, number] | null;
  /** Lo que se confirmó que ocurrió, o `null` mientras nadie lo ha contestado. */
  readonly resultado: "ocurrio" | "no-ocurrio" | null;
}

/**
 * La ficha de un niño para el terapeuta.
 *
 * Todo sale de `GET /children/{id}` y `GET /children/{id}/history`: ninguna
 * cifra de aquí se calcula en el servidor a propósito, porque son agregados de
 * lectura y no hechos clínicos nuevos.
 */
export interface FichaNino {
  readonly id: string;
  readonly etiqueta: string;
  /** El último riesgo estimado, 0-100, o `null` si el modelo se abstiene. */
  readonly riesgo: number | null;
  readonly serie: readonly PuntoRiesgo[];
  /**
   * Tasa observada de episodios: confirmados que sí, sobre confirmados totales.
   *
   * `null` con menos de `MINIMO_RESULTADOS` confirmados. No es una cifra
   * pequeña ni provisional: es la misma abstención que hace el backend, y
   * enseñar "1 de 2 = 50 %" sería inventar una tasa con dos datos.
   */
  readonly tasa: TasaObservada | null;
  /** Días con formulario, sobre los días que abarca el historial. */
  readonly adherencia: number;
  /** Preguntas de cierre sin contestar. Es trabajo pendiente, no un dato. */
  readonly pendientes: number;
  readonly perfilSensorial: readonly string[];
  readonly apoyosComunicacion: readonly string[];
  readonly contraindicaciones: readonly string[];
}

export interface TasaObservada {
  readonly episodios: number;
  readonly confirmados: number;
}

/**
 * Lo que se puede decir del conjunto de los niños.
 *
 * Son cuentas, no medias. Un riesgo medio de la cartera no significaría nada
 * —cada niño tiene su propia línea base, y promediar líneas base distintas es
 * exactamente lo que el producto se niega a hacer—, así que el widget cuenta
 * cuántos hay en cada banda y cuánto trabajo queda abierto.
 */
export interface ResumenConjunto {
  readonly ninos: number;
  readonly porBanda: Readonly<Record<"alto" | "medio" | "bajo" | "desconocido", number>>;
  /** Preguntas de cierre sin contestar en toda la cartera. */
  readonly pendientes: number;
  /** Niños con al menos un día registrado en el historial que se leyó. */
  readonly conRegistro: number;
  /** Días registrados sobre días posibles, en toda la cartera, 0-1. */
  readonly adherencia: number;
}

/* Vocabulario visible. Vive junto al tipo para que añadir un valor obligue a
   dar su etiqueta. */

export const ETIQUETA_RESULTADO: Record<"ocurrio" | "no-ocurrio", string> = {
  ocurrio: "Episodio confirmado",
  "no-ocurrio": "Sin episodio",
};

export const ETIQUETA_DECISION: Record<"approved" | "rejected", string> = {
  approved: "Aprobada",
  rejected: "Rechazada",
};
