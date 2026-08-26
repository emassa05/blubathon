<script setup lang="ts">
defineProps<{
  /** Día visible, ya formateado: "Martes 25". */
  etiqueta: string;
}>();

defineEmits<{
  diaAnterior: [];
  diaSiguiente: [];
}>();
</script>

<template>
  <nav class="fecha" aria-label="Navegación por día">
    <button
      type="button"
      class="fecha__chevron"
      aria-label="Día anterior"
      @click="$emit('diaAnterior')"
    >
      <span aria-hidden="true">&lsaquo;</span>
    </button>

    <!-- El propio rótulo es la región viva: al cambiar de día se anuncia. -->
    <p class="fecha__etiqueta" aria-live="polite" aria-atomic="true">{{ etiqueta }}</p>

    <button
      type="button"
      class="fecha__chevron"
      aria-label="Día siguiente"
      @click="$emit('diaSiguiente')"
    >
      <span aria-hidden="true">&rsaquo;</span>
    </button>
  </nav>
</template>

<style scoped>
.fecha {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--faro-esp-22);
}

.fecha__etiqueta {
  font-size: var(--faro-fs-20);
  font-weight: 700;
  color: var(--faro-texto-fuerte);
}

.fecha__chevron {
  display: grid;
  place-items: center;
  min-width: var(--faro-toque);
  min-height: var(--faro-toque);
  /* El área táctil crece a 44x44 sin mover el trazo: el margen negativo
     devuelve el espacio que el padding le robaría al `gap` de 22. */
  margin-inline: calc((var(--faro-toque) - var(--faro-fs-26)) / -2);
  font-size: var(--faro-fs-26);
  line-height: 1;
  color: var(--faro-texto-suave);
  border-radius: var(--faro-radio-10);
}

.fecha__chevron:focus-visible {
  outline: var(--faro-foco-grosor) solid var(--faro-foco-panel);
  outline-offset: var(--faro-foco-offset);
}
</style>
