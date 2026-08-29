/**
 * Un texto que se escribe solo, en vez de aparecer puesto.
 *
 * Es el hermano de `useNumeroAnimado` y por la misma razón: la recomendación no
 * está ahí desde el principio, llega después de que el RAG la redacte. Verla
 * aparecer entera de golpe no cuenta que acaba de escribirse; verla escribirse
 * sí, y además es la única señal de que la espera terminó para quien no estaba
 * mirando la tarjeta en ese instante.
 *
 * Como allí, es `requestAnimationFrame` y nada más: sin librería y sin un
 * temporizador por carácter, que con la pestaña de fondo se acumularía y
 * soltaría el texto a trompicones al volver.
 *
 * Dos decisiones que no son obvias:
 *
 * - **El recorrido tiene techo.** A un ritmo fijo por carácter, una
 *   recomendación de setecientos caracteres tardaría casi medio minuto y
 *   dejaría de ser un remate para ser otra espera. Con el techo, un texto corto
 *   se escribe a ritmo de máquina y uno largo cabe igual en `MS_MAXIMO`.
 * - **Escribir se pide, no se deduce.** El composable no vigila ningún `ref`:
 *   quien llama decide si este texto llega —y se escribe— o si ya estaba —y se
 *   pone—. Hojear días hacia atrás no es que llegue nada, y retecleando la
 *   recomendación de cada día la pantalla parecería estar trabajando cuando no
 *   lo está.
 *
 * Y respeta `prefers-reduced-motion`: quien pide menos movimiento recibe el
 * texto puesto, no una versión lenta del tecleo.
 */

import { onScopeDispose, readonly, ref } from "vue";

/**
 * Ritmo de tecleo mientras el texto quepa en el techo.
 *
 * Se ve escribir, que es el punto: a treinta caracteres por segundo la frase
 * aparece de un tirón y lo único que queda de la animación es un parpadeo.
 */
export const MS_POR_CARACTER = 32;

/**
 * Y lo que dura como mucho el recorrido entero, sea cual sea el largo.
 *
 * Una recomendación ronda los setecientos caracteres, así que en la práctica es
 * este número y no el de arriba el que manda en la tarjeta. Cinco segundos es
 * lo que tarda en leerse un párrafo así: el texto termina de escribirse más o
 * menos cuando termina de leerse, y no se espera a nada.
 */
export const MS_MAXIMO = 5000;

function prefiereMenosMovimiento(): boolean {
  return typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function useMaquinaDeEscribir(inicial = "") {
  const mostrado = ref(inicial);
  let cuadro: number | null = null;

  function parar(): void {
    if (cuadro !== null && typeof cancelAnimationFrame === "function") {
      cancelAnimationFrame(cuadro);
    }
    cuadro = null;
  }

  /** El texto, ya puesto. Corta cualquier tecleo a medias. */
  function poner(texto: string): void {
    parar();
    mostrado.value = texto;
  }

  /** El texto, escribiéndose desde el principio. */
  function escribir(texto: string): void {
    parar();

    if (texto === "" || typeof requestAnimationFrame !== "function" || prefiereMenosMovimiento()) {
      mostrado.value = texto;
      return;
    }

    const cuanto = Math.min(texto.length * MS_POR_CARACTER, MS_MAXIMO);
    const inicio = performance.now();
    mostrado.value = "";

    const paso = (ahora: number): void => {
      const avance = Math.min(1, (ahora - inicio) / cuanto);
      // `ceil` y no `round`: al primer fotograma ya hay un carácter escrito, así
      // que el párrafo nunca se queda vacío una vuelta de reloj.
      mostrado.value = texto.slice(0, Math.ceil(texto.length * avance));
      if (avance === 1) {
        parar();
        return;
      }
      cuadro = requestAnimationFrame(paso);
    };

    cuadro = requestAnimationFrame(paso);
  }

  onScopeDispose(parar);

  return { mostrado: readonly(mostrado), poner, escribir };
}
