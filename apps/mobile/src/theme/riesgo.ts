/**
 * Bandas de riesgo: el único sitio donde vive el corte entre un estado y otro.
 *
 * La banda no pinta nada por sí misma. Elige una clase, y esa clase lleva la
 * paleta entera —panel, curvas de nivel, textos y tarjeta de recomendación— en
 * `styles/tokens.css`. Añadir una banda es añadir aquí su corte y allí su
 * paleta: ningún componente cambia.
 */

/**
 * `desconocido` no es un cuarto nivel de riesgo: es la ausencia de estimación.
 * El modelo se abstiene cuando no tiene resultados verificados suficientes
 * (SPEC 8.5), y pintar eso de celeste lo leería como riesgo bajo.
 */
export const BANDAS_RIESGO = ["desconocido", "bajo", "medio", "alto"] as const;

export type BandaRiesgo = (typeof BANDAS_RIESGO)[number];

/**
 * Cortes en % de riesgo.
 *
 * Son los mismos que el backend usa para su `risk_band` (`p ≥ 0.5 → high`,
 * `0.2 ≤ p < 0.5 → medium`, `p < 0.2 → low`). Tienen que serlo: cuando la API
 * declara la banda —en la recomendación de hoy— la pantalla usa la suya, y dos
 * juegos de cortes harían que el color se contradijera con el dato.
 */
export const CORTE_MEDIO = 20;
export const CORTE_ALTO = 50;

/** `null` es abstención del modelo, no un riesgo de cero. */
export function bandaRiesgo(riesgo: number | null): BandaRiesgo {
  if (riesgo === null) return "desconocido";
  if (riesgo >= CORTE_ALTO) return "alto";
  if (riesgo >= CORTE_MEDIO) return "medio";
  return "bajo";
}

/** La banda tal como la declara la API, cuando la declara. */
export const BANDA_DE_LA_API: Record<"low" | "medium" | "high" | "unknown", BandaRiesgo> = {
  low: "bajo",
  medium: "medio",
  high: "alto",
  unknown: "desconocido",
};

export const CLASE_BANDA: Record<BandaRiesgo, string> = {
  desconocido: "blubathon-banda--desconocido",
  bajo: "blubathon-banda--bajo",
  medio: "blubathon-banda--medio",
  alto: "blubathon-banda--alto",
};
