<script setup lang="ts">
/**
 * Una respuesta posible: la fila entera, con su texto al principio y nada más.
 *
 * Sin marca a la izquierda y sin borde. Lo que dice si está elegida es el
 * relleno —verde lleno, texto en blanco— y el peso del texto, que es lo que se
 * sigue viendo sin distinguir tonos. Para quien navega con lector lo dice
 * `aria-pressed`, que es lo único que hace falta ahí.
 *
 * Dos tonos:
 *
 * - **elección**: verde, mientras se contesta.
 * - **repaso**: azul, cuando la respuesta viene de una sugerencia que se está
 *   repasando antes de guardar. Es la misma fila: lo que cambia es que eso no lo
 *   eligió nadie todavía, lo propone Blubathon.
 */
withDefaults(
  defineProps<{
    etiqueta: string;
    marcada?: boolean;
    /** El tono de lo marcado: la elección de siempre, o el repaso final. */
    tono?: "eleccion" | "repaso";
  }>(),
  { marcada: false, tono: "eleccion" },
);
</script>

<template>
  <button
    type="button"
    class="opcion"
    :class="[`opcion--${tono}`, { 'opcion--marcada': marcada }]"
    :aria-pressed="marcada"
  >
    {{ etiqueta }}
  </button>
</template>

<style scoped>
.opcion {
  width: 100%;
  min-height: 56px;
  padding: var(--blubathon-esp-12) var(--blubathon-esp-18);
  font-size: var(--blubathon-fs-15);
  font-weight: 600;
  color: var(--blubathon-opcion-texto);
  text-align: start;
  background: var(--blubathon-opcion-fondo);
  border-radius: var(--blubathon-radio-pastilla);
}

.opcion:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-foco-oscuro);
  outline-offset: var(--blubathon-foco-offset);
}

.opcion--marcada {
  font-weight: 700;
  color: var(--blubathon-opcion-texto-fuerte);
  background: var(--blubathon-opcion-elegida-fondo);
  /* Se levanta: una sombra se ve sin distinguir colores —ver `tokens.css`. */
  box-shadow: var(--blubathon-elev-1);
}

.opcion--repaso.opcion--marcada {
  color: var(--blubathon-opcion-repaso-texto);
  background: var(--blubathon-opcion-repaso-fondo);
}
</style>
