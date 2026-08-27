<script setup lang="ts">
import type { Semana } from "@/dominio/semana";

defineProps<{ semana: Semana }>();

defineEmits<{
  semanaAnterior: [];
  semanaSiguiente: [];
}>();
</script>

<template>
  <nav class="semana" aria-label="Navegación por semana">
    <button
      type="button"
      class="semana__chevron"
      aria-label="Semana anterior"
      @click="$emit('semanaAnterior')"
    >
      <span aria-hidden="true">&lsaquo;</span>
    </button>

    <!-- El rótulo es la región viva: al cambiar de semana se anuncia una vez. -->
    <p class="semana__etiqueta" aria-live="polite" aria-atomic="true">
      <span class="oculto-visual">{{ semana.etiquetaAccesible }}</span>
      <span aria-hidden="true">{{ semana.etiqueta }}</span>
    </p>

    <button
      type="button"
      class="semana__chevron"
      aria-label="Semana siguiente"
      @click="$emit('semanaSiguiente')"
    >
      <span aria-hidden="true">&rsaquo;</span>
    </button>
  </nav>
</template>

<style scoped>
/* Tres hijos y ninguno de ancho variable: el rótulo, con `flex: 1`, queda
   centrado entre los dos chevrones. El botón "Esta semana" era un cuarto hijo
   que le robaba ancho y corría la fecha a la izquierda. */
.semana {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--blubathon-esp-12);
}

.semana__etiqueta {
  flex: 1;
  font-size: var(--blubathon-fs-155);
  font-weight: 700;
  color: var(--blubathon-marca-profundo);
  text-align: center;
}

/* Mismo patrón que el navegador de día: el área táctil crece a 44 y el margen
   negativo devuelve lo que el padding le robaría al hueco. */
.semana__chevron {
  display: grid;
  flex: none;
  place-items: center;
  min-width: var(--blubathon-toque);
  min-height: var(--blubathon-toque);
  font-size: var(--blubathon-fs-26);
  line-height: 1;
  color: var(--blubathon-marca-accion);
  border-radius: var(--blubathon-radio-10);
}

.semana__chevron:hover {
  background: var(--blubathon-fila-activa);
}

.semana__chevron:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-foco-oscuro);
  outline-offset: var(--blubathon-foco-offset);
}
</style>
