/**
 * El fondo de la página: un degradado suave con burbujas, en varias versiones.
 *
 * Existe porque el blanco plano de debajo del panel hacía que la pantalla se
 * viera clínica. Lo que va aquí es ambiente, no información: la cifra, la banda
 * y las ondas siguen siendo lo único que dice algo del día, y el fondo no puede
 * competir con ellos ni cambiar de significado según cuál toque.
 *
 * De ahí las reglas que cumplen todas las variantes:
 *
 * - **Muy poco croma y mucha claridad.** Las burbujas viven entre 0.93 y 0.97
 *   de luminancia con croma bajo 0.06. Sobre eso, una tarjeta blanca sigue
 *   leyéndose como blanca, que es lo que la separa del fondo.
 * - **Grandes y pocas.** Tres manchas anchas y difusas, nunca un patrón que se
 *   repita: un patrón se convierte en textura y la textura pide atención.
 * - **Dentro de la familia de la marca.** Los tonos se mueven entre 205 y 275,
 *   así que ninguna variante se lee como una banda de riesgo.
 *
 * La variante se sortea una vez al arrancar y no vuelve a cambiar mientras la
 * pantalla está abierta: que cambie sola bajo los pies sería un efecto, no una
 * ambientación.
 */

export interface VarianteFondo {
  /** Nombre corto, para depurar y para los tests. */
  readonly id: string;
  /** El valor completo de `background`, capas de burbuja sobre el degradado. */
  readonly capas: string;
}

/**
 * Los tamaños van en porcentaje, así que cada capa se dimensiona contra la caja
 * que la pinta: la columna de contenido. Eso hace que se vean iguales en un
 * teléfono de 390 y en una ventana de escritorio, donde la columna sigue
 * midiendo 480. Anclarlas a la ventana las estiraba hasta desaparecer.
 */
export const VARIANTES: readonly VarianteFondo[] = [
  {
    id: "alba",
    capas: [
      "radial-gradient(62% 44% at 14% 6%, oklch(0.945 0.054 245 / 0.87), transparent 70%)",
      "radial-gradient(46% 34% at 92% 30%, oklch(0.955 0.050 205 / 0.82), transparent 72%)",
      "radial-gradient(74% 46% at 58% 98%, oklch(0.955 0.044 265 / 0.77), transparent 74%)",
      "linear-gradient(180deg, oklch(0.99 0.010 245), oklch(0.975 0.018 240))",
    ].join(", "),
  },
  {
    id: "marea",
    capas: [
      "radial-gradient(54% 40% at 88% 4%, oklch(0.95 0.052 225 / 0.87), transparent 70%)",
      "radial-gradient(58% 42% at 6% 44%, oklch(0.955 0.048 260 / 0.80), transparent 72%)",
      "radial-gradient(66% 40% at 74% 92%, oklch(0.96 0.042 210 / 0.77), transparent 74%)",
      "linear-gradient(180deg, oklch(0.988 0.012 235), oklch(0.972 0.020 248))",
    ].join(", "),
  },
  {
    id: "calma",
    capas: [
      "radial-gradient(70% 46% at 50% 0%, oklch(0.955 0.046 250 / 0.82), transparent 68%)",
      "radial-gradient(44% 32% at 10% 62%, oklch(0.95 0.052 215 / 0.77), transparent 72%)",
      "radial-gradient(48% 34% at 94% 76%, oklch(0.955 0.048 270 / 0.77), transparent 72%)",
      "linear-gradient(180deg, oklch(0.99 0.009 250), oklch(0.974 0.017 236))",
    ].join(", "),
  },
  {
    id: "brisa",
    capas: [
      "radial-gradient(50% 36% at 22% 18%, oklch(0.95 0.056 268 / 0.82), transparent 70%)",
      "radial-gradient(62% 44% at 96% 56%, oklch(0.955 0.046 232 / 0.80), transparent 74%)",
      "radial-gradient(58% 38% at 34% 96%, oklch(0.96 0.042 250 / 0.74), transparent 72%)",
      "linear-gradient(180deg, oklch(0.989 0.011 240), oklch(0.973 0.019 252))",
    ].join(", "),
  },
  {
    id: "sereno",
    capas: [
      "radial-gradient(58% 40% at 78% 10%, oklch(0.952 0.050 255 / 0.84), transparent 70%)",
      "radial-gradient(52% 38% at 4% 30%, oklch(0.95 0.054 220 / 0.78), transparent 72%)",
      "radial-gradient(72% 44% at 62% 100%, oklch(0.958 0.042 240 / 0.76), transparent 74%)",
      "linear-gradient(180deg, oklch(0.99 0.010 242), oklch(0.975 0.016 244))",
    ].join(", "),
  },
];

/** La propiedad que leen las superficies de página. */
export const VARIABLE_FONDO = "--faro-fondo-pagina";

/** Una variante al azar. Sin argumento usa `Math.random`. */
export function varianteAlAzar(sorteo: number = Math.random()): VarianteFondo {
  const indice = Math.floor(Math.min(Math.max(sorteo, 0), 0.999999) * VARIANTES.length);
  // `VARIANTES` no está vacío, pero el tipo no lo sabe.
  return VARIANTES[indice] ?? VARIANTES[0]!;
}

/**
 * Fija la variante en el documento.
 *
 * Se escribe en `:root` y no en un componente porque el fondo lo pintan varias
 * superficies —el contorno de la página, la columna de Salud, el historial— y
 * todas tienen que sacar el mismo valor de un solo sitio.
 */
export function aplicarFondo(
  raiz: HTMLElement = document.documentElement,
  variante: VarianteFondo = varianteAlAzar(),
): VarianteFondo {
  raiz.style.setProperty(VARIABLE_FONDO, variante.capas);
  // Queda a la vista en el DOM: es lo que permite reproducir una captura sin
  // adivinar cuál salió.
  raiz.dataset.fondo = variante.id;
  return variante;
}
