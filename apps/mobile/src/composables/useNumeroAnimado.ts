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

/** Lo que tarda la cifra en llegar. Corta: es un remate, no una espera. */
export const MS_CUENTA = 900;

/**
 * Frena al final en vez de a velocidad constante: la cifra llega y se posa, que
 * es lo que hace que se lea el número de destino y no el movimiento.
 */
function suavizar(avance: number): number {
  return 1 - (1 - avance) ** 3;
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
  function sinAnimacion(): boolean {
    return (
      duracion <= 0 || typeof requestAnimationFrame !== "function" || prefiereMenosMovimiento()
    );
  }

  function parar(): void {
    if (cuadro !== null && typeof cancelAnimationFrame === "function") {
      cancelAnimationFrame(cuadro);
    }
    cuadro = null;
  }

  function animar(hasta: number | null): void {
    parar();

    const desde = mostrado.value;
    if (hasta === null || desde === null || desde === hasta || sinAnimacion()) {
      mostrado.value = hasta;
      return;
    }

    const inicio = performance.now();
    const recorrido = hasta - desde;

    const paso = (ahora: number): void => {
      const avance = Math.min(1, (ahora - inicio) / duracion);
      mostrado.value = avance === 1 ? hasta : Math.round(desde + recorrido * suavizar(avance));
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
  function reiniciar(): void {
    const hasta = destino.value;
    if (hasta === null || sinAnimacion()) return;
    mostrado.value = 0;
    animar(hasta);
  }

  watch(destino, animar);
  onScopeDispose(parar);

  return { mostrado: readonly(mostrado), reiniciar };
}
