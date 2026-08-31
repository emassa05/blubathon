/**
 * La comprobación de la cohorte, traída al día que se está mirando.
 *
 * El backend publica la calibración por tramos: de los días que se anunciaron
 * como riesgo bajo, medio o alto, en cuántos hubo episodio de verdad. Aquí solo
 * se elige el tramo que le toca a la cifra de hoy y se le pone forma de frase.
 *
 * Es lo que sustituyó al "nivel de confianza". Aquel salía de la anchura del
 * intervalo del modelo y por eso se quedaba clavado en 79-80% con cualquier
 * historial establecido: medía cuántos días había, no si el número acertaba, y
 * se leía como lo segundo. Esto se lee como lo que es —"de los días así, ocurrió
 * en tantos"— y se puede desmentir.
 *
 * Los umbrales no se escriben aquí: la banda la manda el servidor con cada
 * tramo, y el de hoy se busca por el mismo corte que usa la API.
 */

import type { CalibrationBand, CalibrationResponse } from "@/api/contrato";
import { intervalo } from "@/dominio/incertidumbre";

/** Los mismos cortes que `risk_band_for` en el servidor, sobre 0-100. */
export function bandaDeRiesgo(riesgo: number): CalibrationBand["band"] {
  if (riesgo >= 50) return "high";
  if (riesgo >= 20) return "medium";
  return "low";
}

export interface Comprobacion {
  readonly banda: CalibrationBand["band"];
  /** Con cuántos días se comprobó. Sin esto el intervalo no se sabe leer. */
  readonly dias: number;
  /** La frecuencia observada, 0-100. */
  readonly observado: number;
  /** El intervalo de Wilson al 95%, 0-100. */
  readonly intervalo: readonly [number, number];
  /** Si lo anunciado cae dentro del intervalo: los días no lo desmienten. */
  readonly concuerda: boolean;
}

/**
 * Cuántos días hacen falta antes de enseñar un tramo.
 *
 * Por debajo el intervalo es tan ancho que no dice nada: con ocho días abarca
 * cuarenta puntos y "concuerda" con casi cualquier cosa. Enseñarlo igual daría
 * la impresión de que algo está comprobado cuando lo único comprobado es que
 * todavía no hay datos, así que por debajo de esto no se enseña nada.
 */
export const DIAS_MINIMOS = 25;

const REDONDEO = (valor: number): number => Math.round(valor * 100);

export function comprobacionDe(
  calibracion: CalibrationResponse | null,
  riesgo: number | null,
): Comprobacion | null {
  if (calibracion === null || riesgo === null) return null;

  const banda = bandaDeRiesgo(riesgo);
  const tramo = (calibracion.bands ?? []).find(
    (candidato: CalibrationBand) => candidato.band === banda,
  );
  if (tramo === undefined || tramo.days < DIAS_MINIMOS) return null;

  // El generador publica `interval` como `Array<unknown>`, así que se estrecha
  // con el mismo criterio que el intervalo del modelo y no con otro: dos
  // maneras de decidir si un intervalo sirve acabarían enseñando bandas que la
  // otra había descartado.
  const rango = intervalo(tramo.interval);
  if (rango === null) return null;
  const [bajo, alto] = rango;

  return {
    banda,
    dias: tramo.days,
    observado: REDONDEO(tramo.observed),
    intervalo: [REDONDEO(bajo), REDONDEO(alto)],
    concuerda: bajo <= tramo.announced && tramo.announced <= alto,
  };
}
