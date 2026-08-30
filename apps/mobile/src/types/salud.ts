/** Tipos del dominio de la pantalla Salud. Nombres de dominio en español. */

import type { CalibrationResponse } from "@/api/contrato";

export type IconoFactor = "luna" | "rombo";

/**
 * El diseño solo especificaba "Alta prioridad", y el tipo quedó abierto a más
 * niveles: basta añadir la clave aquí y en `ETIQUETA_PRIORIDAD`.
 *
 * `media` es el segundo nivel que pedían las variables críticas: una respuesta
 * fuera de lo habitual no es lo mismo que una en nivel alto, y pintar las dos
 * igual haría que ninguna se leyera. La pastilla usa el mismo par de colores
 * del aviso pendiente, así que no entra ningún color nuevo.
 */
export type PrioridadFactor = "alta" | "media";

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

/**
 * En qué punto está la redacción del consejo del día.
 *
 * `pendiente` es el único estado que se mueve solo: el RAG está redactando y la
 * respuesta llega después, así que es el único que la tarjeta anima. Los otros
 * tres son finales.
 */
export type EstadoRedaccion = "pendiente" | "lista" | "abstenida" | "sin-formulario";

export interface Recomendacion {
  readonly texto: string;
  readonly estado: EstadoRedaccion;
}

/**
 * Días seguidos sin un episodio confirmado.
 *
 * `dias` cuenta solo resultados confirmados con un "no": un día sin contestar no
 * es un día sin desregulación, y contarlo como tal convertiría el silencio en
 * una buena noticia. Por eso la racha se mide desde el último día **resuelto**
 * —`desde`— y no desde hoy.
 */
export interface RachaSinDesregulacion {
  readonly dias: number;
  /** Fecha ISO del último día con resultado confirmado. */
  readonly hasta: string;
}

/**
 * Lo que la pantalla necesita saber de un día. Es el contrato con la API:
 * `adaptadores/resumenSalud.ts` lo arma desde las respuestas del backend y
 * ningún componente ve nada más.
 */
export interface ResumenSalud {
  /** Fecha ISO 8601 (YYYY-MM-DD) del día que muestra la pantalla. */
  readonly fecha: string;
  /**
   * Riesgo de desregulación del día, 0-100. Elige la ilustración de cabecera.
   *
   * `null` es abstención del modelo, no riesgo cero: sin resultados verificados
   * suficientes el backend no estima, y la pantalla no puede inventar una
   * cifra ni pintarla de "bajo".
   */
  readonly riesgo: number | null;
  /**
   * Confianza del modelo en ese riesgo, 0-100.
   *
   * `null` cuando no hay estimación **o** cuando el track que estimó no publica
   * intervalo —el challenger logístico no lo hace—. Ninguno de los dos casos se
   * rellena con un número.
   */
  /**
   * La calibración de la cohorte, tal como la publica la API.
   *
   * Cruda y no ya resuelta al tramo de hoy: el tramo depende de la cifra, y
   * `comprobacionDe` los junta donde se pintan. Guardarla entera deja además
   * enseñar los otros tramos sin pedirla otra vez.
   */
  readonly calibracion: CalibrationResponse | null;
  readonly recomendacion: Recomendacion;
  readonly factores: readonly FactorRiesgo[];
  readonly formularios: readonly RegistroFormulario[];
  readonly formularioPendiente: boolean;
  /** `null` mientras no haya ni un solo resultado confirmado. */
  readonly rachaSinDesregulacion: RachaSinDesregulacion | null;
}

/* Vocabulario visible. Vive junto al tipo para que añadir un valor obligue a
   dar su etiqueta. */

export const ETIQUETA_PRIORIDAD: Record<PrioridadFactor, string> = {
  alta: "Alta prioridad",
  media: "Atención",
};

export const ETIQUETA_ESTADO_FORMULARIO: Record<EstadoFormulario, string> = {
  respondido: "Respondido",
  "sin-responder": "Sin responder",
};
