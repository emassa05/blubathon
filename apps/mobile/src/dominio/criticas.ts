/**
 * Variables críticas del día.
 *
 * Una variable crítica es una respuesta que se sale de lo habitual de esa
 * persona —dormir mucho menos de lo que suele— o que está en un nivel alto por
 * sí misma —desregulación frecuente, medicación no tomada—. No es un
 * diagnóstico ni una predicción: es una señal para mirar el día con atención.
 *
 * **La API no devuelve esto.** El historial (`GET /children/{id}/history`) trae
 * el día, su episodio, su estimación y su recomendación, pero no las
 * respuestas; ningún endpoint publica las respuestas de un envío, y
 * `FormPlanResponse` solo dice qué preguntar y qué sugerir. Así que se calcula
 * aquí, sobre las respuestas que esta aplicación guarda al enviarlas
 * (`estado/respuestas.ts`).
 *
 * Dos familias de reglas, y ninguna inventa una política que el repositorio ya
 * tenga declarada:
 *
 * 1. **Desviación personal.** Con suficiente historial propio, un valor
 *    numérico es anómalo si su z robusta (mediana y MAD) llega al corte
 *    declarado en `ROBUST_Z_ANOMALY` (C17), sobre la ventana de
 *    `PERSONAL_DEVIATION_WINDOW_DAYS` (C21) y con al menos
 *    `PERSONAL_MIN_OBSERVATIONS` (C22) observaciones. Un valor de un campo
 *    nominal es anómalo si su frecuencia personal queda por debajo de
 *    `CATEGORICAL_ANOMALY_PROBABILITY` (C16).
 * 2. **Nivel alto.** Sin historial suficiente no hay desviación que calcular,
 *    así que se mira el valor contra los cortes de la tabla de abajo. Son
 *    cortes de interfaz —para decidir qué se destaca en pantalla—, no cortes
 *    clínicos: no hay ninguna banda operativa publicada y esta pantalla no se
 *    inventa una.
 */

import { BLUBATHON_CONSTANTS, type FieldCode, type ValorCampo } from "@/api/contrato";
import { etiquetaCampo, formatearValor, ordenCanonico } from "@/dominio/campos";
import type { IconoFactor } from "@/types/salud";

export type SeveridadCritica = "alta" | "media";

export interface VariableCritica {
  readonly campo: FieldCode;
  readonly titulo: string;
  /** El valor del día, ya escrito para leerse. */
  readonly valor: string;
  /** Por qué se destaca: "Bajo lo habitual", "Desregulación frecuente"… */
  readonly motivo: string;
  readonly severidad: SeveridadCritica;
  readonly icono: IconoFactor;
}

/** Una frase, la misma siempre, sobre lo que estas variables son y no son. */
export const AVISO_VARIABLES_CRITICAS =
  "Estas respuestas se salen de lo habitual o están en un nivel alto, y pueden " +
  "influir en cómo le vaya el día. No son un diagnóstico.";

/** Ventana, mínimo de observaciones y cortes de anomalía, declarados en C16-C22. */
const VENTANA_DIAS = BLUBATHON_CONSTANTS.C21.value;
const MINIMO_OBSERVACIONES = BLUBATHON_CONSTANTS.C22.value;
const CORTE_Z_ROBUSTA = BLUBATHON_CONSTANTS.C17.value;
const CORTE_FRECUENCIA = BLUBATHON_CONSTANTS.C16.value;

/** Constante de la z robusta: la MAD por 0.6745 estima la desviación típica. */
const FACTOR_MAD = 0.6745;

/** Los campos que hablan del sueño llevan luna; el resto, rombo. */
const CAMPOS_DE_SUENO: readonly FieldCode[] = [
  "sleep_hours",
  "sleep_quality",
  "night_awakenings",
  "wake_state",
];

function iconoDe(campo: FieldCode): IconoFactor {
  return CAMPOS_DE_SUENO.includes(campo) ? "luna" : "rombo";
}

interface Hallazgo {
  readonly severidad: SeveridadCritica;
  readonly motivo: string;
}

type ReglaDeNivel = (valor: ValorCampo) => Hallazgo | null;

function numero(valor: ValorCampo): number | null {
  return typeof valor === "number" ? valor : null;
}

/**
 * Cortes de nivel por campo. Cada uno responde a la misma pregunta: mirando
 * solo este día, ¿hay algo que merezca destacarse? Un campo sin entrada aquí
 * nunca es crítico por nivel; sí puede serlo por desviación personal.
 */
const REGLAS_DE_NIVEL: Partial<Record<FieldCode, ReglaDeNivel>> = {
  sleep_hours: (valor) => {
    const horas = numero(valor);
    if (horas === null) return null;
    if (horas < 6) return { severidad: "alta", motivo: "Muy poco sueño" };
    if (horas < 7) return { severidad: "media", motivo: "Sueño corto" };
    if (horas > 13) return { severidad: "media", motivo: "Sueño más largo de lo esperable" };
    return null;
  },
  sleep_quality: (valor) => {
    if (valor === "interrupted") return { severidad: "media", motivo: "Sueño interrumpido" };
    if (valor === "sleep_onset_difficulty") {
      return { severidad: "media", motivo: "Costó quedarse dormido" };
    }
    return null;
  },
  night_awakenings: (valor) => {
    const veces = numero(valor);
    if (veces === null) return null;
    if (veces >= 5) return { severidad: "alta", motivo: "Muchos despertares" };
    if (veces >= 3) return { severidad: "media", motivo: "Varios despertares" };
    return null;
  },
  wake_state: (valor) =>
    valor === "irritable_crying" ? { severidad: "media", motivo: "Despertar irritable" } : null,
  morning_support_need: (valor) => {
    const apoyo = numero(valor);
    if (apoyo === null) return null;
    if (apoyo >= 5) return { severidad: "alta", motivo: "Necesitó apoyo constante" };
    if (apoyo >= 4) return { severidad: "media", motivo: "Necesitó apoyo frecuente" };
    return null;
  },
  gi_status: (valor) =>
    valor === "constipation" || valor === "diarrhea"
      ? { severidad: "media", motivo: "Malestar gastrointestinal" }
      : null,
  medication_adherence: (valor) =>
    valor === "missed" ? { severidad: "alta", motivo: "No tomó la medicación" } : null,
  routine_changes: (valor) =>
    valor === true ? { severidad: "media", motivo: "Cambio en la rutina" } : null,
  alertness: (valor) => {
    if (valor === "high") return { severidad: "media", motivo: "Alerta alta" };
    if (valor === "low") return { severidad: "media", motivo: "Alerta baja" };
    return null;
  },
  dysregulation_event_count: (valor) => {
    const episodios = numero(valor);
    if (episodios === null) return null;
    if (episodios >= 3) return { severidad: "alta", motivo: "Varios episodios en el día" };
    if (episodios >= 1) return { severidad: "media", motivo: "Hubo episodios" };
    return null;
  },
  daily_regulation_state: (valor) =>
    valor === "frequent_dysregulation"
      ? { severidad: "alta", motivo: "Desregulación frecuente" }
      : null,
  activity_participation: (valor) => {
    const participacion = numero(valor);
    return participacion !== null && participacion <= 2
      ? { severidad: "media", motivo: "Participó poco" }
      : null;
  },
  social_interactions: (valor) => {
    const interaccion = numero(valor);
    return interaccion !== null && interaccion <= 2
      ? { severidad: "media", motivo: "Poca interacción" }
      : null;
  },
  eating_status: (valor) => {
    const comida = numero(valor);
    return comida !== null && comida <= 2 ? { severidad: "media", motivo: "Comió poco" } : null;
  },
  relevant_event_flag: (valor) =>
    valor === true ? { severidad: "media", motivo: "Pasó algo fuera de lo común" } : null,
};

function mediana(valores: readonly number[]): number {
  const ordenados = [...valores].sort((uno, otro) => uno - otro);
  const medio = Math.floor(ordenados.length / 2);
  const central = ordenados[medio] ?? 0;
  if (ordenados.length % 2 === 1) return central;
  return ((ordenados[medio - 1] ?? central) + central) / 2;
}

/** Z robusta con mediana y MAD. `null` cuando no hay dispersión que medir. */
export function zRobusta(valor: number, historial: readonly number[]): number | null {
  if (historial.length < MINIMO_OBSERVACIONES) return null;
  const centro = mediana(historial);
  const desviacion = mediana(historial.map((punto) => Math.abs(punto - centro)));
  if (desviacion === 0) return null;
  return (FACTOR_MAD * (valor - centro)) / desviacion;
}

function desviacionNumerica(
  campo: FieldCode,
  valor: number,
  historial: readonly number[],
): Hallazgo | null {
  const z = zRobusta(valor, historial);
  if (z === null || Math.abs(z) < CORTE_Z_ROBUSTA) return null;
  const centro = mediana(historial);
  const referencia = formatearValor(campo, Number(centro.toFixed(1)));
  const direccion = valor < centro ? "Bajo lo habitual" : "Sobre lo habitual";
  return { severidad: "media", motivo: `${direccion}, suele ser ${referencia}` };
}

function desviacionCategorica(valor: string, historial: readonly string[]): Hallazgo | null {
  if (historial.length < MINIMO_OBSERVACIONES) return null;
  const veces = historial.filter((punto) => punto === valor).length;
  if (veces / historial.length >= CORTE_FRECUENCIA) return null;
  return { severidad: "media", motivo: "Poco habitual en su historial" };
}

/** Un día del historial local con sus respuestas, para poder comparar. */
export interface DiaConRespuestas {
  readonly fecha: string;
  readonly respuestas: Readonly<Partial<Record<FieldCode, ValorCampo>>>;
}

function historialDeCampo(
  campo: FieldCode,
  dias: readonly DiaConRespuestas[],
  fecha: string,
): ValorCampo[] {
  const desde = new Date(`${fecha}T00:00:00`);
  desde.setDate(desde.getDate() - VENTANA_DIAS);
  const mes = String(desde.getMonth() + 1).padStart(2, "0");
  const limite = `${desde.getFullYear()}-${mes}-${String(desde.getDate()).padStart(2, "0")}`;

  const valores: ValorCampo[] = [];
  for (const dia of dias) {
    if (dia.fecha >= fecha || dia.fecha < limite) continue;
    const valor = dia.respuestas[campo];
    if (valor !== undefined) valores.push(valor);
  }
  return valores;
}

/** La más grave de las dos, con la que llegó primero ganando el empate. */
function peor(uno: Hallazgo | null, otro: Hallazgo | null): Hallazgo | null {
  if (uno === null) return otro;
  if (otro === null) return uno;
  return uno.severidad === "alta" ? uno : otro;
}

/**
 * Las variables críticas de un día, de la más grave a la menos.
 *
 * `anteriores` son los días ya guardados de esa misma persona; con menos de
 * `PERSONAL_MIN_OBSERVATIONS` en la ventana, la desviación personal no se
 * calcula y solo quedan los cortes de nivel.
 */
export function variablesCriticas(
  respuestas: Readonly<Partial<Record<FieldCode, ValorCampo>>>,
  fecha: string,
  anteriores: readonly DiaConRespuestas[] = [],
): readonly VariableCritica[] {
  const encontradas: VariableCritica[] = [];

  for (const [clave, valor] of Object.entries(respuestas)) {
    if (valor === undefined) continue;
    const campo = clave as FieldCode;
    const historial = historialDeCampo(campo, anteriores, fecha);

    let hallazgo = REGLAS_DE_NIVEL[campo]?.(valor) ?? null;
    if (typeof valor === "number") {
      const numeros = historial.filter((punto): punto is number => typeof punto === "number");
      hallazgo = peor(hallazgo, desviacionNumerica(campo, valor, numeros));
    } else if (typeof valor === "string") {
      const textos = historial.filter((punto): punto is string => typeof punto === "string");
      hallazgo = peor(hallazgo, desviacionCategorica(valor, textos));
    }
    if (hallazgo === null) continue;

    encontradas.push({
      campo,
      titulo: etiquetaCampo(campo),
      valor: formatearValor(campo, valor),
      motivo: hallazgo.motivo,
      severidad: hallazgo.severidad,
      icono: iconoDe(campo),
    });
  }

  return encontradas.sort((uno, otro) => {
    if (uno.severidad !== otro.severidad) return uno.severidad === "alta" ? -1 : 1;
    return ordenCanonico(uno.campo) - ordenCanonico(otro.campo);
  });
}
