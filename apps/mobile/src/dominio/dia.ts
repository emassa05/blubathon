/**
 * Un día, con todo lo que la pantalla sabe de él.
 *
 * Junta las dos mitades que hoy viven en sitios distintos: lo que la API
 * devuelve del día (`ChildHistoryDay`: episodio, estimación, recomendación y
 * resultado) y las respuestas que este dispositivo guardó al enviarlo, que son
 * las que permiten calcular sus variables críticas.
 */

import type { ChildHistoryDay, FieldCode, ValorCampo } from "@/api/contrato";
import { variablesCriticas, type DiaConRespuestas, type VariableCritica } from "@/dominio/criticas";
import type { DiaCalendario } from "@/dominio/semana";
import { bandaRiesgo, type BandaRiesgo } from "@/theme/riesgo";

export type EstadoDia = "respondido" | "sin-responder" | "futuro";

export interface ResumenDia {
  readonly fecha: string;
  readonly estado: EstadoDia;
  /** El envío está guardado aquí pero la API todavía no lo devuelve. */
  readonly soloLocal: boolean;
  readonly episodioId: string | null;
  /** Probabilidad del track personal, 0-1, o `null` si el modelo se abstuvo. */
  readonly probabilidad: number | null;
  /** `true` cuando hubo estimación pero el modelo se abstuvo de dar número. */
  readonly estimacionAbstenida: boolean;
  readonly recomendacion: ChildHistoryDay["recommendation"];
  readonly resultado: ChildHistoryDay["outcome"];
  readonly respuestas: Readonly<Partial<Record<FieldCode, ValorCampo>>> | undefined;
  readonly criticas: readonly VariableCritica[];
}

/** La banda de color de un día, solo si ese día tiene un número que mostrar. */
export function bandaDelDia(resumen: ResumenDia): BandaRiesgo | null {
  if (resumen.probabilidad === null) return null;
  return bandaRiesgo(Math.round(resumen.probabilidad * 100));
}

export function resumenDeDia(
  fecha: string,
  hoy: string,
  dia: ChildHistoryDay | undefined,
  respuestas: Readonly<Partial<Record<FieldCode, ValorCampo>>> | undefined,
  anteriores: readonly DiaConRespuestas[] = [],
): ResumenDia {
  const respondido = dia !== undefined || respuestas !== undefined;
  const estado: EstadoDia = respondido ? "respondido" : fecha > hoy ? "futuro" : "sin-responder";

  return {
    fecha,
    estado,
    soloLocal: dia === undefined && respuestas !== undefined,
    episodioId: dia?.prediction_episode_id ?? null,
    probabilidad: dia?.prediction?.probability ?? null,
    estimacionAbstenida: dia?.prediction?.status === "abstained",
    recomendacion: dia?.recommendation ?? null,
    resultado: dia?.outcome ?? null,
    respuestas,
    criticas: respuestas === undefined ? [] : variablesCriticas(respuestas, fecha, anteriores),
  };
}

/** Una celda del calendario: el día del almanaque y lo que se sabe de él. */
export interface CeldaCalendario {
  readonly dia: DiaCalendario;
  readonly resumen: ResumenDia;
}
