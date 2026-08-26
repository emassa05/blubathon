/**
 * Las respuestas que se han enviado desde este dispositivo, por día.
 *
 * Existe por una razón concreta: **la API no las devuelve**. Se pueden enviar
 * (`POST /children/{id}/forms`), pero ningún endpoint publica las respuestas de
 * un envío, así que sin esta copia local no se podría ni releer un cuestionario
 * ya contestado ni calcular las variables críticas de un día pasado.
 *
 * Es una copia, no la fuente de verdad: la verdad es el envío que aceptó la
 * API. Si se borran los datos del navegador, el historial de la API sigue
 * intacto y lo único que se pierde es el detalle de las respuestas.
 *
 * Vive en `localStorage` bajo una clave versionada. Si el navegador lo prohíbe
 * —modo privado, almacenamiento bloqueado—, todo sigue funcionando en memoria
 * durante la sesión.
 */

import { ref } from "vue";

import type { FieldCode, ValorCampo } from "@/api/contrato";
import type { DiaConRespuestas } from "@/dominio/criticas";

export type RespuestasDelDia = Partial<Record<FieldCode, ValorCampo>>;

/** niño → fecha ISO → respuestas de ese día. */
type Almacen = Record<string, Record<string, RespuestasDelDia>>;

const CLAVE = "faro.respuestas.v1";

function leerDelDisco(): Almacen {
  try {
    const crudo = window.localStorage.getItem(CLAVE);
    return crudo === null ? {} : (JSON.parse(crudo) as Almacen);
  } catch {
    return {};
  }
}

const almacen = ref<Almacen>(leerDelDisco());

function escribirEnDisco(): void {
  try {
    window.localStorage.setItem(CLAVE, JSON.stringify(almacen.value));
  } catch {
    // Sin almacenamiento, la copia vive solo lo que dure la sesión.
  }
}

/** Las respuestas guardadas de un día, o `undefined` si ese día no se envió. */
export function respuestasDe(ninoId: string, fecha: string): RespuestasDelDia | undefined {
  return almacen.value[ninoId]?.[fecha];
}

/** Todos los días guardados de esa persona, del más reciente al más antiguo. */
export function diasConRespuestas(ninoId: string): readonly DiaConRespuestas[] {
  const porFecha = almacen.value[ninoId] ?? {};
  return Object.entries(porFecha)
    .map(([fecha, respuestas]) => ({ fecha, respuestas }))
    .sort((uno, otro) => (uno.fecha < otro.fecha ? 1 : -1));
}

/** Guarda lo enviado. Se llama cuando la API ya aceptó el envío, nunca antes. */
export function guardarRespuestas(
  ninoId: string,
  fecha: string,
  respuestas: RespuestasDelDia,
): void {
  almacen.value = {
    ...almacen.value,
    [ninoId]: { ...(almacen.value[ninoId] ?? {}), [fecha]: { ...respuestas } },
  };
  escribirEnDisco();
}

/** Vacía la copia local. Solo lo usan las pruebas. */
export function olvidarRespuestas(): void {
  almacen.value = {};
  escribirEnDisco();
}
