<script setup lang="ts">
import type { Semana } from "@/dominio/semana";

defineProps<{ semana: Semana }>();

defineEmits<{
  semanaAnterior: [];
  semanaSiguiente: [];
  semanaActual: [];
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

    <!-- Solo aparece cuando hay a dónde volver: si ya estás en esta semana, un
         botón que no hace nada es ruido. -->
    <button
      v-if="!semana.esSemanaActual"
      type="button"
      class="semana__hoy"
      @click="$emit('semanaActual')"
    >
      Esta semana
    </button>
  </nav>
</template>

<style scoped>
.semana {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: var(--faro-esp-12);
}

.semana__etiqueta {
  flex: 1;
  font-size: var(--faro-fs-155);
  font-weight: 700;
  color: var(--faro-verde-profundo);
  text-align: center;
}

/* Mismo patrón que el navegador de día: el área táctil crece a 44 y el margen
   negativo devuelve lo que el padding le robaría al hueco. */
.semana__chevron {
  display: grid;
  flex: none;
  place-items: center;
  min-width: var(--faro-toque);
  min-height: var(--faro-toque);
  font-size: var(--faro-fs-26);
  line-height: 1;
  color: var(--faro-verde-accion);
  border-radius: var(--faro-radio-10);
}

.semana__chevron:hover {
  background: var(--faro-fila-activa);
}

.semana__chevron:focus-visible {
  outline: var(--faro-foco-grosor) solid var(--faro-foco-oscuro);
  outline-offset: var(--faro-foco-offset);
}

.semana__hoy {
  min-height: var(--faro-toque);
  padding-inline: var(--faro-esp-14);
  font-size: var(--faro-fs-125);
  font-weight: 700;
  color: var(--faro-verde-accion);
  background: var(--faro-superficie);
  border: 1px solid var(--faro-linea);
  border-radius: var(--faro-radio-pastilla);
}

.semana__hoy:focus-visible {
  outline: var(--faro-foco-grosor) solid var(--faro-foco-oscuro);
  outline-offset: var(--faro-foco-offset);
}
</style>
