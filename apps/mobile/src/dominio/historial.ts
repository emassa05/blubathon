/**
 * Un día, una fila.
 *
 * `GET /history` devuelve **una fila por sesión enviada**, no por día. Nada
 * impide enviar el cuestionario dos veces el mismo `local_date` —y reabrir un
 * día ya enviado para corregir algo es justo lo que la pantalla ofrece—, así
 * que ese día vuelve partido en dos filas, de la más reciente a la más antigua.
 *
 * Y las dos filas no dicen lo mismo. El segundo envío se enlaza al episodio que
 * ya estaba abierto (`episode_linked`), así que su fila trae el
 * `submission_id` nuevo y **nada más**: sin episodio, sin estimación, sin
 * recomendación y sin resultado, porque todo eso cuelga del primer envío.
 *
 * Quedarse con la primera fila —lo que hacía este código— tiraba justo lo que
 * había: el día se quedaba sin cifra de riesgo, sin recomendación y sin el
 * resultado ya confirmado, y la racha dejaba de contarlo. Quedarse con la
 * última sería igual de arbitrario al revés: perdería el envío nuevo.
 *
 * Así que no se elige una fila, se juntan: para cada dato, el primero que
 * exista mirando de la más reciente a la más antigua. El envío es el último que
 * se hizo y el episodio, la estimación, la recomendación y el resultado son los
 * del día, los tenga la fila que los tenga.
 */

import type { ChildHistoryDay } from "@/api/contrato";

function presente<T>(valor: T | null | undefined): valor is T {
  return valor !== null && valor !== undefined;
}

/**
 * Junta en una las filas que comparten `local_date`.
 *
 * Conserva el orden de llegada —del día más reciente al más antiguo, que es el
 * del contrato y del que dependen la racha y el calendario— y coloca cada día
 * en la posición de su fila más reciente.
 *
 * @param dias Los días tal y como los devuelve `GET /history`.
 */
export function unificarPorDia(dias: readonly ChildHistoryDay[]): readonly ChildHistoryDay[] {
  const porFecha = new Map<string, ChildHistoryDay>();

  for (const dia of dias) {
    const previo = porFecha.get(dia.local_date);

    if (previo === undefined) {
      porFecha.set(dia.local_date, dia);
      continue;
    }

    // `previo` es la fila más reciente de este día: lo suyo manda y esta solo
    // rellena los huecos que aquella dejó.
    porFecha.set(dia.local_date, {
      local_date: dia.local_date,
      submission_id: presente(previo.submission_id) ? previo.submission_id : dia.submission_id,
      prediction_episode_id: presente(previo.prediction_episode_id)
        ? previo.prediction_episode_id
        : dia.prediction_episode_id,
      prediction: presente(previo.prediction) ? previo.prediction : dia.prediction,
      recommendation: presente(previo.recommendation) ? previo.recommendation : dia.recommendation,
      outcome: presente(previo.outcome) ? previo.outcome : dia.outcome,
    });
  }

  return [...porFecha.values()];
}
