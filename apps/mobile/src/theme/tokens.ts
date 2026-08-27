/**
 * Tokens que necesita la lógica (no el CSS): nombres de animación, rango de
 * duración y el nombre de la variable CSS que la transporta.
 *
 * Los colores, radios y tamaños viven en `styles/tokens.css`. Aquí solo entra
 * lo que TypeScript tiene que poder comprobar.
 */

export const ANIMACIONES_AVISO = ["pulso", "aparicion", "deslizamiento"] as const;

export type AnimacionAviso = (typeof ANIMACIONES_AVISO)[number];

export const ANIMACION_AVISO_POR_DEFECTO: AnimacionAviso = "pulso";

/** Segundos. Rango y paso del control de duración del aviso. */
export const DURACION_AVISO = {
  minimo: 3,
  maximo: 9,
  paso: 0.5,
  porDefecto: 5,
} as const;

/** Clase que activa cada animación. Los `@keyframes` viven en `AvisoPendiente`. */
export const CLASE_ANIMACION: Record<AnimacionAviso, string> = {
  pulso: "aviso--pulso",
  aparicion: "aviso--aparicion",
  deslizamiento: "aviso--deslizamiento",
};

/** Variable CSS por la que viaja la duración. Nunca se escriben keyframes desde JS. */
export const VARIABLE_DURACION = "--blubathon-dur";

/** Recorta al rango y ajusta al paso declarados en `DURACION_AVISO`. */
export function normalizarDuracion(segundos: number): number {
  const { minimo, maximo, paso } = DURACION_AVISO;
  if (!Number.isFinite(segundos)) return DURACION_AVISO.porDefecto;
  const acotado = Math.min(maximo, Math.max(minimo, segundos));
  return Math.round(acotado / paso) * paso;
}
