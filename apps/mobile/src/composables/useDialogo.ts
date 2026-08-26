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
 */

import { onBeforeUnmount, onMounted, type Ref } from "vue";

const FOCALIZABLES = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(", ");

export function useDialogo(contenedor: Ref<HTMLElement | null>, cerrar: () => void): void {
  let anterior: HTMLElement | null = null;
  let desbordeAnterior = "";

  function focalizables(): HTMLElement[] {
    const raiz = contenedor.value;
    if (raiz === null) return [];
    return Array.from(raiz.querySelectorAll<HTMLElement>(FOCALIZABLES));
  }

  function alPulsarTecla(evento: KeyboardEvent): void {
    if (evento.key === "Escape") {
      evento.preventDefault();
      cerrar();
      return;
    }
    if (evento.key !== "Tab") return;

    const controles = focalizables();
    const primero = controles[0];
    const ultimo = controles[controles.length - 1];
    if (primero === undefined || ultimo === undefined) return;

    const activo = document.activeElement;
    if (evento.shiftKey && (activo === primero || !contenedor.value?.contains(activo))) {
      evento.preventDefault();
      ultimo.focus();
      return;
    }
    if (!evento.shiftKey && activo === ultimo) {
      evento.preventDefault();
      primero.focus();
    }
  }

  onMounted(() => {
    anterior = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    desbordeAnterior = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", alPulsarTecla);
    // El primer control del diálogo, y si no lo hubiera, el propio diálogo.
    (focalizables()[0] ?? contenedor.value)?.focus();
  });

  onBeforeUnmount(() => {
    document.removeEventListener("keydown", alPulsarTecla);
    document.body.style.overflow = desbordeAnterior;
    anterior?.focus();
  });
}
