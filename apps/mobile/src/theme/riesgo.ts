/**
 * Bandas de riesgo: el único sitio donde vive el corte entre un estado y otro.
 *
 * La banda no pinta nada por sí misma. Elige una clase, y esa clase lleva la
 * paleta entera —panel, curvas de nivel, textos y tarjeta de recomendación— en
 * `styles/tokens.css`. Añadir una banda es añadir aquí su corte y allí su
 * paleta: ningún componente cambia.
 */

export const BANDAS_RIESGO = ["bajo", "medio", "alto"] as const;

export type BandaRiesgo = (typeof BANDAS_RIESGO)[number];

/** Cortes del diseño, en % de riesgo. El 25 justo cae en "medio". */
export const CORTE_MEDIO = 25;
export const CORTE_ALTO = 50;

export function bandaRiesgo(riesgo: number): BandaRiesgo {
  if (riesgo < CORTE_MEDIO) return "bajo";
  if (riesgo <= CORTE_ALTO) return "medio";
  return "alto";
}

export const CLASE_BANDA: Record<BandaRiesgo, string> = {
  bajo: "faro-banda--bajo",
  medio: "faro-banda--medio",
  alto: "faro-banda--alto",
};

export const ETIQUETA_BANDA: Record<BandaRiesgo, string> = {
  bajo: "Bajo",
  medio: "Medio",
  alto: "Alto",
};

/**
 * Un riesgo representativo de cada banda.
 *
 * TODO(spec): solo lo usa el botón de prueba de `SaludView`, que es temporal.
 * Cuando la pantalla reciba datos reales, esto y el botón se van juntos.
 */
export const RIESGO_DE_PRUEBA: Record<BandaRiesgo, number> = {
  bajo: 18,
  medio: 38,
  alto: 72,
};

/**
 * La banda siguiente, en círculo. Para el botón de prueba.
 *
 * Va como tabla y no como `indexOf` + módulo: el índice es correcto por
 * construcción pero el tipo no lo sabe, y una tabla obliga a decidir el
 * siguiente al añadir una banda en vez de dejar que el orden lo decida solo.
 */
const SIGUIENTE: Record<BandaRiesgo, BandaRiesgo> = {
  bajo: "medio",
  medio: "alto",
  alto: "bajo",
};

export function bandaSiguiente(banda: BandaRiesgo): BandaRiesgo {
  return SIGUIENTE[banda];
}
