/**
 * Lo que se puede decir del conjunto de los niños.
 *
 * El widget de abajo a la derecha del panel enseña esto, y lo que enseña son
 * **cuentas**, no medias. La razón es la misma que sostiene el producto entero:
 * cada niño tiene su propia línea base, y un "riesgo medio de la cartera" sería
 * la media de cifras que no comparten escala. Cuántos hay en riesgo alto sí
 * significa algo; el promedio de sus probabilidades no.
 *
 * Y nada más que eso: el conjunto responde a quién mirar primero. La adherencia
 * y los cierres pendientes son trabajo de cada niño, y en la fila de su niño se
 * pueden hacer; sumados en una cifra de cartera no se pueden.
 */

import { bandaRiesgo, type BandaRiesgo } from "@/theme/riesgo";
import type { FichaNino, ResumenConjunto } from "@/types/terapeuta";

export function resumirConjunto(fichas: readonly FichaNino[]): ResumenConjunto {
  const porBanda: Record<BandaRiesgo, number> = {
    desconocido: 0,
    bajo: 0,
    medio: 0,
    alto: 0,
  };

  for (const ficha of fichas) {
    porBanda[bandaRiesgo(ficha.riesgo)] += 1;
  }

  return { ninos: fichas.length, porBanda };
}
