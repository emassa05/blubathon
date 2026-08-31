/**
 * La serie de riesgo de un niño, a partir de su historial.
 *
 * Es la traducción de `GET /children/{id}/history` a algo que se pueda dibujar:
 * el contrato devuelve los días del más reciente al más antiguo, y una línea de
 * tiempo se lee al revés, así que aquí se invierte una vez y ningún componente
 * vuelve a preocuparse por el orden.
 *
 * Dos decisiones que no son de dibujo sino de qué se puede afirmar:
 *
 * - La probabilidad del contrato es 0-1 y aquí pasa a 0-100, que es la escala
 *   en la que ya habla el resto de la interfaz (`bandaRiesgo`, `CabeceraRiesgo`).
 *   Tener dos escalas conviviendo es cómo se acaba pintando un 0.8 de riesgo
 *   como si fuera un 0.8 %.
 * - Una abstención entra como `null` y no se salta. Si se filtrara, la línea
 *   uniría el día de antes con el de después y dibujaría una pendiente que
 *   nadie estimó; el hueco es el dato.
 */

import type { ChildHistoryDay } from "@/api/contrato";
import { intervalo } from "@/dominio/incertidumbre";
import type { PuntoRiesgo, TasaObservada } from "@/types/terapeuta";

/** Resultados confirmados que hacen falta antes de publicar una tasa (C19). */
export const MINIMO_RESULTADOS = 5;

function porcentaje(probabilidad: number): number {
  return Math.round(probabilidad * 1000) / 10;
}

/** Lo que se confirmó de un día, o `null` si sigue sin respuesta. */
function resultado(dia: ChildHistoryDay): "ocurrio" | "no-ocurrio" | null {
  const estado = dia.outcome?.status;
  if (estado === "yes") return "ocurrio";
  if (estado === "no") return "no-ocurrio";
  // `pending`, `unknown` y `conflicted` no son un "no": son días sin respuesta,
  // y pintarlos como limpios convertiría el silencio en una buena noticia.
  return null;
}

/**
 * @param dias Historial tal y como lo devuelve el contrato, del más reciente al
 *   más antiguo.
 * @returns Los mismos días en orden cronológico, listos para dibujar.
 */
export function serieRiesgo(dias: readonly ChildHistoryDay[]): PuntoRiesgo[] {
  return [...dias].reverse().map((dia) => {
    const prediccion = dia.prediction;
    const estimado = prediccion?.status === "ok" ? (prediccion.probability ?? null) : null;
    const rango = prediccion?.status === "ok" ? intervalo(prediccion.interval) : null;

    return {
      fecha: dia.local_date,
      riesgo: estimado === null ? null : porcentaje(estimado),
      banda: rango === null ? null : ([porcentaje(rango[0]), porcentaje(rango[1])] as const),
      resultado: resultado(dia),
    };
  });
}

/** El último riesgo estimado, saltándose las abstenciones más recientes. */
export function ultimoRiesgo(serie: readonly PuntoRiesgo[]): number | null {
  for (let indice = serie.length - 1; indice >= 0; indice -= 1) {
    const punto = serie[indice];
    if (punto !== undefined && punto.riesgo !== null) return punto.riesgo;
  }
  return null;
}

/**
 * La tasa observada del niño: episodios confirmados sobre resultados
 * confirmados.
 *
 * Se abstiene por debajo de `MINIMO_RESULTADOS`, con el mismo corte que usa el
 * backend para su línea base. No es prudencia decorativa: con dos resultados,
 * "1 de 2" se lee como un 50 % de riesgo de fondo y no es nada parecido a eso.
 */
export function tasaObservada(serie: readonly PuntoRiesgo[]): TasaObservada | null {
  const confirmados = serie.filter((punto) => punto.resultado !== null);
  if (confirmados.length < MINIMO_RESULTADOS) return null;
  return {
    episodios: confirmados.filter((punto) => punto.resultado === "ocurrio").length,
    confirmados: confirmados.length,
  };
}

/**
 * Días con formulario sobre días que abarca el historial, 0-1.
 *
 * El denominador son los días que el historial cubre —de la primera fecha a la
 * última—, no los días que trae: `GET /history` devuelve solo días con envío,
 * así que contar filas sobre filas daría siempre 1 y no mediría nada.
 */
export function adherencia(serie: readonly PuntoRiesgo[]): number {
  if (serie.length === 0) return 0;
  const primera = serie[0];
  const ultima = serie[serie.length - 1];
  if (primera === undefined || ultima === undefined) return 0;

  const dias = diasEntre(primera.fecha, ultima.fecha) + 1;
  return dias <= 0 ? 0 : Math.min(1, serie.length / dias);
}

/** Días de calendario entre dos fechas ISO. Se comparan en UTC a mediodía para
 *  que ningún cambio de hora mueva la cuenta un día. */
function diasEntre(desde: string, hasta: string): number {
  const inicio = Date.parse(`${desde}T12:00:00Z`);
  const fin = Date.parse(`${hasta}T12:00:00Z`);
  if (Number.isNaN(inicio) || Number.isNaN(fin)) return 0;
  return Math.round((fin - inicio) / 86_400_000);
}

/** Preguntas de cierre sin contestar en el historial que se leyó. */
export function pendientesDeCierre(dias: readonly ChildHistoryDay[]): number {
  return dias.filter((dia) => {
    const estado = dia.outcome?.status;
    return estado === "pending" || estado === "unknown" || estado === "conflicted";
  }).length;
}
