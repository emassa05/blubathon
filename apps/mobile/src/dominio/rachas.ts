/**
 * Días seguidos sin un episodio de desregulación.
 *
 * Es la única cifra buena de la pantalla, así que hay que tener cuidado con de
 * qué está hecha. Un día solo entra en la racha si alguien confirmó que **no**
 * ocurrió: `pending`, `unknown` y `conflicted` no son días limpios, son días sin
 * respuesta, y contarlos convertiría el silencio del cuidador en una buena
 * noticia que nadie ha dado.
 *
 * De ahí las dos reglas:
 *
 * - Se empieza a contar en el último día **resuelto**, no en hoy. La pregunta de
 *   hoy suele estar abierta —la ventana de 24 h no ha cerrado— y arrancar ahí
 *   dejaría la racha en cero cada mañana.
 * - Desde ahí se cuenta hacia atrás y se para en el primer día que no sea un
 *   `no`. Un `yes` corta, y un hueco sin contestar también: detrás de él no se
 *   sabe qué pasó.
 *
 * Por eso el resultado lleva `hasta`: la racha se cuenta hasta ese día, no hasta
 * hoy, y la pantalla lo dice.
 */

import type { ChildHistoryDay } from "@/api/contrato";
import type { RachaSinDesregulacion } from "@/types/salud";

/** El resultado confirmado de un día, o `null` si todavía no lo hay. */
function resuelto(dia: ChildHistoryDay): "yes" | "no" | null {
  const estado = dia.outcome?.status;
  return estado === "yes" || estado === "no" ? estado : null;
}

/**
 * @param dias Los días del historial. `GET /history` los devuelve del más
 *   reciente al más antiguo y aquí se asume ese orden, que es el del contrato.
 */
export function rachaSinDesregulacion(
  dias: readonly ChildHistoryDay[],
): RachaSinDesregulacion | null {
  // Los días de arriba sin resolver no cortan la racha: todavía no dicen nada.
  const desde = dias.findIndex((dia) => resuelto(dia) !== null);
  if (desde === -1) return null;

  const hasta = dias[desde]?.local_date;
  if (hasta === undefined) return null;

  let cuenta = 0;
  for (let indice = desde; indice < dias.length; indice += 1) {
    const dia = dias[indice];
    if (dia === undefined || resuelto(dia) !== "no") break;
    cuenta += 1;
  }

  return { dias: cuenta, hasta };
}
