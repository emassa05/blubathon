/**
 * El periodo del que habla una pregunta de cierre, escrito para leerse.
 *
 * Desde que la pantalla ofrece todas las preguntas abiertas a la vez puede
 * haber dos —la que abrió el envío de ayer, con la ventana ya cumplida, y la
 * que acaba de abrir el de hoy— y las dos preguntan lo mismo palabra por
 * palabra. Lo único que las separa es de qué 24 horas hablan, así que ese
 * periodo deja de ser un detalle del contrato y pasa a ir escrito debajo del
 * titular: sin él, dos tarjetas idénticas se leen como la misma preguntada dos
 * veces, que es justo lo que se quería evitar.
 *
 * Se nombra en relativo —"ayer", "hoy"— porque una ventana de resultado nunca
 * está lejos: vence a las 48 h. Más allá de eso se cae al día del almanaque,
 * que es lo que se lee sin tener que contar.
 */

import type { OutcomeRequestView } from "@/api/contrato";

const FORMATO_HORA = new Intl.DateTimeFormat("es-ES", {
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

const FORMATO_DIA = new Intl.DateTimeFormat("es-ES", { weekday: "long", day: "numeric" });

const MS_POR_DIA = 86_400_000;

/** La medianoche local de esa fecha: comparar días, no instantes. */
function medianoche(fecha: Date): number {
  return new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate()).getTime();
}

/** "hoy", "ayer", "mañana" o "el viernes 28", visto desde `ahora`. */
function nombreDelDia(fecha: Date, ahora: Date): string {
  const dias = Math.round((medianoche(ahora) - medianoche(fecha)) / MS_POR_DIA);
  if (dias === 0) return "hoy";
  if (dias === 1) return "ayer";
  if (dias === -1) return "mañana";
  return `el ${FORMATO_DIA.format(fecha)}`;
}

/** "Desde ayer 21:30 hasta hoy 21:30". */
export function ventanaEnPalabras(solicitud: OutcomeRequestView, ahora = new Date()): string {
  const inicio = new Date(Date.parse(solicitud.target_start_at));
  const fin = new Date(Date.parse(solicitud.target_end_at));
  const desde = `${nombreDelDia(inicio, ahora)} ${FORMATO_HORA.format(inicio)}`;
  const hasta = `${nombreDelDia(fin, ahora)} ${FORMATO_HORA.format(fin)}`;
  return `Desde ${desde} hasta ${hasta}`;
}
