/**
 * Lo que se puede decir del conjunto de los niños.
 *
 * El widget de abajo a la derecha del panel enseña esto, y lo que enseña son
 * **cuentas**, no medias. La razón es la misma que sostiene el producto entero:
 * cada niño tiene su propia línea base, y un "riesgo medio de la cartera" sería
 * la media de cifras que no comparten escala. Cuántos hay en riesgo alto sí
 * significa algo; el promedio de sus probabilidades no.
 *
 * Por lo mismo no hay una cifra de adherencia por niño promediada: se suman los
 * días registrados y los días posibles de toda la cartera, y se divide una vez.
 * Promediar porcentajes daría el mismo peso a quien lleva tres días que a quien
 * lleva dos meses.
 */

import { bandaRiesgo, type BandaRiesgo } from "@/theme/riesgo";
import type { FichaNino, ResumenConjunto } from "@/types/terapeuta";

/** Denominador de la adherencia: días que cubre el historial de una ficha. */
function diasPosibles(ficha: FichaNino): number {
  return ficha.adherencia <= 0 ? 0 : Math.round(ficha.serie.length / ficha.adherencia);
}

export function resumirConjunto(fichas: readonly FichaNino[]): ResumenConjunto {
  const porBanda: Record<BandaRiesgo, number> = {
    desconocido: 0,
    bajo: 0,
    medio: 0,
    alto: 0,
  };

  let registrados = 0;
  let posibles = 0;

  for (const ficha of fichas) {
    porBanda[bandaRiesgo(ficha.riesgo)] += 1;
    registrados += ficha.serie.length;
    posibles += diasPosibles(ficha);
  }

  return {
    ninos: fichas.length,
    porBanda,
    pendientes: fichas.reduce((total, ficha) => total + ficha.pendientes, 0),
    conRegistro: fichas.filter((ficha) => ficha.serie.length > 0).length,
    adherencia: posibles === 0 ? 0 : registrados / posibles,
  };
}
