<script setup lang="ts">
import { computed } from "vue";

import type { CeldaCalendario } from "@/dominio/dia";

const props = defineProps<{ celdas: readonly CeldaCalendario[] }>();

const respondidos = computed(
  () => props.celdas.filter((celda) => celda.resumen.estado === "respondido").length,
);

/** Los días que ya pasaron y se quedaron sin cuestionario. Un futuro no cuenta. */
const pendientes = computed(
  () => props.celdas.filter((celda) => celda.resumen.estado === "sin-responder").length,
);

const criticas = computed(() =>
  props.celdas.reduce((total, celda) => total + celda.resumen.criticas.length, 0),
);
</script>

<template>
  <ul class="resumen">
    <li class="cifra">
      <span class="cifra__dato">{{ respondidos }} / 7</span>
      <span class="cifra__rotulo">Respondidos</span>
    </li>
    <li class="cifra">
      <span class="cifra__dato">{{ pendientes }}</span>
      <span class="cifra__rotulo">Sin responder</span>
    </li>
    <li class="cifra">
      <span class="cifra__dato cifra__dato--critica">{{ criticas }}</span>
      <span class="cifra__rotulo">Variables críticas</span>
    </li>
  </ul>
</template>

<style scoped>
/*
 * Tres cifras y sus rótulos. Van en la misma tarjeta y no en tres, porque son
 * la misma frase: cómo fue la semana.
 */
.resumen {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  padding: var(--faro-esp-14) var(--faro-esp-8);
  background: var(--faro-superficie);
  border-radius: var(--faro-radio-24);
  box-shadow: var(--faro-elev-1);
}

.cifra {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--faro-esp-4);
  text-align: center;
}

.cifra + .cifra {
  border-left: 1px solid var(--faro-linea);
}

.cifra__dato {
  font-size: var(--faro-fs-20);
  font-weight: 700;
  color: var(--faro-marca-profundo);
}

.cifra__dato--critica {
  color: var(--faro-critica-media-texto);
}

.cifra__rotulo {
  padding-inline: var(--faro-esp-4);
  font-size: var(--faro-fs-11);
  font-weight: 700;
  letter-spacing: var(--faro-track-012);
  text-transform: uppercase;
  color: var(--faro-gris-texto);
}
</style>
