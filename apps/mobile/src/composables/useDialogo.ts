/**
 * El patrón de diálogo, que es lo que separa un popup de una caja bonita.
 *
 * Cuatro cosas, y las cuatro son de accesibilidad, no de estilo:
 *
 * - El foco entra en el diálogo al abrirlo.
 * - `Tab` y `Mayús+Tab` dan la vuelta dentro, sin salirse al fondo.
 * - `Esc` lo cierra.
 * - Al cerrarlo, el foco vuelve exactamente al control que lo abrió.
 *
 * Además bloquea el desplazamiento de la página de debajo, que si no se mueve
 * sola mientras se desplaza el contenido del diálogo.
 *
 * Dos cosas más, que llegaron con el aviso obligatorio:
 *
 * - **Hay una pila.** Un diálogo puede abrir otro encima, y entonces `Esc` y el
 *   ciclo de tabulación son solo del de arriba. Sin la pila, una sola pulsación
 *   de `Esc` cerraba los dos a la vez y el trampeo de foco de los dos se
 *   peleaba por el mismo `Tab`.
 * - **`Esc` se puede desactivar.** Un diálogo obligatorio no se cierra sin
 *   contestar, y eso incluye el teclado: la tecla no cae al diálogo de debajo,
 *   simplemente no hace nada.
 *
 * El bloqueo del desplazamiento se cuenta, no se pisa: con dos diálogos
 * abiertos, cerrar el de arriba no le devuelve el desplazamiento a la página.
 */

import { onBeforeUnmount, watch, type Ref } from "vue";

const FOCALIZABLES = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(", ");

/** Los diálogos abiertos, de más antiguo a más reciente. */
const pila: symbol[] = [];

/** Cuántos diálogos tienen tomado el desplazamiento de la página. */
let bloqueos = 0;
let desbordeOriginal = "";

export interface OpcionesDialogo {
  /** `false` en un diálogo obligatorio: `Esc` no lo cierra ni cierra otro. */
  readonly cerrarConEsc?: () => boolean;
}

export function useDialogo(
  contenedor: Ref<HTMLElement | null>,
  cerrar: () => void,
  opciones: OpcionesDialogo = {},
): void {
  const ficha = Symbol("dialogo");
  const cerrarConEsc = opciones.cerrarConEsc ?? (() => true);

  let anterior: HTMLElement | null = null;
  let activo = false;

  function focalizables(): HTMLElement[] {
    const raiz = contenedor.value;
    if (raiz === null) return [];
    return Array.from(raiz.querySelectorAll<HTMLElement>(FOCALIZABLES));
  }

  function alPulsarTecla(evento: KeyboardEvent): void {
    // Solo el de arriba responde. El de debajo sigue montado y con su escucha
    // puesta, pero mientras haya uno encima no es el diálogo con el que se
    // está hablando.
    if (pila[pila.length - 1] !== ficha) return;

    if (evento.key === "Escape") {
      evento.preventDefault();
      if (cerrarConEsc()) cerrar();
      return;
    }
    if (evento.key !== "Tab") return;

    const controles = focalizables();
    const primero = controles[0];
    const ultimo = controles[controles.length - 1];
    if (primero === undefined || ultimo === undefined) return;

    const activoAhora = document.activeElement;
    if (evento.shiftKey && (activoAhora === primero || !contenedor.value?.contains(activoAhora))) {
      evento.preventDefault();
      ultimo.focus();
      return;
    }
    if (!evento.shiftKey && activoAhora === ultimo) {
      evento.preventDefault();
      primero.focus();
    }
  }

  function activar(): void {
    if (activo) return;
    activo = true;

    anterior = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    pila.push(ficha);

    if (bloqueos === 0) desbordeOriginal = document.body.style.overflow;
    bloqueos += 1;
    document.body.style.overflow = "hidden";

    document.addEventListener("keydown", alPulsarTecla);
    // El primer control del diálogo, y si no lo hubiera, el propio diálogo.
    (focalizables()[0] ?? contenedor.value)?.focus();
  }

  function desactivar(): void {
    if (!activo) return;
    activo = false;

    document.removeEventListener("keydown", alPulsarTecla);

    const posicion = pila.indexOf(ficha);
    if (posicion !== -1) pila.splice(posicion, 1);

    bloqueos -= 1;
    if (bloqueos === 0) document.body.style.overflow = desbordeOriginal;

    anterior?.focus();
  }

  /*
   * El contenedor aparece un tic después del montaje: el diálogo entra con una
   * animación y hasta que no arranca no existe el elemento al que llevar el
   * foco. `flush: "post"` espera a que el DOM esté escrito.
   */
  watch(
    contenedor,
    (elemento) => {
      if (elemento !== null) activar();
    },
    { flush: "post", immediate: true },
  );

  onBeforeUnmount(desactivar);
}
