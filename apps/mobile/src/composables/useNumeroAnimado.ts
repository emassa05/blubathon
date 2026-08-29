/**
 * Una cifra que sube hasta su valor en vez de aparecer puesta.
 *
 * Es `requestAnimationFrame` y nada más: sin librería, sin transición CSS —una
 * transición no puede interpolar el texto de un nodo— y sin temporizador, que
 * seguiría corriendo con la pestaña de fondo y llegaría a destino a saltos.
 *
 * Tres cosas que hace y que una interpolación a secas no haría:
 *
 * - **Arranca en el valor anterior, no en cero.** Al pasar de un día con 18 a
 *   uno con 22, la cifra recorre esos cuatro puntos. Volver a cero para subir
 *   otra vez se leería como si el dato se hubiera perdido y hubiera vuelto.
 *
 *   La excepción es `reiniciar`, y es una excepción por lo mismo: después de
 *   enviar el cuestionario la cifra no está corrigiéndose, se está calculando
 *   otra vez con un día más, y recorrerla entera desde cero es lo que hace que
 *   se lea como el resultado de lo que se acaba de contestar.
 * - **Un solo bucle.** Cambiar de valor a media animación no lanza un segundo
 *   `rAF` que compita con el primero por el mismo `ref`.
 * - **Respeta `prefers-reduced-motion`.** Quien pide menos movimiento recibe la
 *   cifra puesta, no una versión lenta de la animación.
 *
 * `null` —la abstención del modelo— no se anima: no hay ningún número que
 * recorrer y el guion aparece y desaparece tal cual.
 */

import { onScopeDispose, readonly, ref, watch, type Ref } from "vue";

/** Lo que tarda la cifra en corregirse de un valor a otro. Corta: es un remate. */
export const MS_CUENTA = 900;

/**
 * Y lo que tarda en recorrerse entera desde cero.
 *
 * El doble, porque el recorrido es otro: corregir 18 por 22 son cuatro puntos y
 * se lee de un vistazo; subir de 0 a 22 es la cifra entera y hay que poder
 * verla pasar. Con los 900 de la corrección la cuenta se acababa antes de que
 * diera tiempo a mirarla.
 */
export const MS_CUENTA_DESDE_CERO = 1800;

/**
 * Frena al final en vez de a velocidad constante: la cifra llega y se posa, que
 * es lo que hace que se lea el número de destino y no el movimiento.
 */
function suavizar(avance: number): number {
  return 1 - (1 - avance) ** 3;
}

/**
 * La curva de la cuenta desde cero: arranca despacio, coge velocidad y vuelve a
 * frenar.
 *
 * `suavizar` no vale aquí y es justo lo que hacía que la cuenta no pareciera
 * empezar en cero. Frenar al final significa correr al principio: con esa curva,
 * al 10% del tiempo la cifra ya va por el 27% del recorrido y al 20% pasa de la
 * mitad. Para cuatro puntos da igual; para la cifra entera, lo que se ve es un
 * número que aparece casi puesto y remata despacio.
 *
 * Esta sale de cero de verdad —al 10% del tiempo lleva un 0.4% del recorrido— y
 * sigue posándose al llegar.
 */
function suavizarDesdeCero(avance: number): number {
  return avance < 0.5 ? 4 * avance ** 3 : 1 - (-2 * avance + 2) ** 3 / 2;
}

function prefiereMenosMovimiento(): boolean {
  return typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function useNumeroAnimado(destino: Ref<number | null>, duracion = MS_CUENTA) {
  const mostrado = ref<number | null>(destino.value);
  let cuadro: number | null = null;

  /**
   * Si en este entorno no hay animación que hacer: sin `rAF` —una prueba, un
   * render de servidor—, sin duración, o porque se pidió menos movimiento.
   * Entonces la cifra se pone y ya está.
   */
  function sinAnimacion(cuanto: number): boolean {
    return (
      cuanto <= 0 || typeof requestAnimationFrame !== "function" || prefiereMenosMovimiento()
    );
  }

  function parar(): void {
    if (cuadro !== null && typeof cancelAnimationFrame === "function") {
      cancelAnimationFrame(cuadro);
    }
    cuadro = null;
  }

  /**
   * @param cuanto Cuánto dura este recorrido.
   * @param curva Cómo reparte el tiempo. Las dos cosas cambian entre corregir
   *   un valor y contar desde cero, y por eso viajan juntas.
   */
  function animar(hasta: number | null, cuanto = duracion, curva = suavizar): void {
    parar();

    const desde = mostrado.value;
    if (hasta === null || desde === null || desde === hasta || sinAnimacion(cuanto)) {
      mostrado.value = hasta;
      return;
    }

    const inicio = performance.now();
    const recorrido = hasta - desde;

    const paso = (ahora: number): void => {
      const avance = Math.min(1, (ahora - inicio) / cuanto);
      mostrado.value = avance === 1 ? hasta : Math.round(desde + recorrido * curva(avance));
      cuadro = avance === 1 ? null : requestAnimationFrame(paso);
    };

    cuadro = requestAnimationFrame(paso);
  }

  /**
   * Vuelve a contar, desde cero hasta el valor que haya ahora.
   *
   * No espera a que el valor cambie, y por eso hace falta: al volver del
   * cuestionario la estimación puede haber salido igual que estaba, y entonces
   * `watch` no dispararía nada y no habría animación ninguna. Lo que se pide
   * aquí no es "anima el cambio" sino "recorre la cifra entera".
   *
   * Con la animación desactivada no hace nada en absoluto: poner un cero para
   * borrarlo en el mismo fotograma sería un parpadeo, y quien pidió menos
   * movimiento pidió justo lo contrario de eso. La cifra ya está puesta.
   */
  function reiniciar(duracionCuenta = MS_CUENTA_DESDE_CERO): void {
    const hasta = destino.value;
    if (hasta === null || sinAnimacion(duracionCuenta)) return;
    mostrado.value = 0;
    animar(hasta, duracionCuenta, suavizarDesdeCero);
  }

  // Con la referencia suelta, `watch` le pasaría el valor viejo como segundo
  // argumento y ese sitio es ahora la duración.
  watch(destino, (nuevo) => animar(nuevo));
  onScopeDispose(parar);

  return { mostrado: readonly(mostrado), reiniciar };
}
