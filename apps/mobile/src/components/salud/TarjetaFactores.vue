<script setup lang="ts">
import type { Component } from "vue";

import IconoLuna from "@/components/icons/IconoLuna.vue";
import IconoRombo from "@/components/icons/IconoRombo.vue";
import { ETIQUETA_PRIORIDAD, type FactorRiesgo, type IconoFactor } from "@/types/salud";

defineProps<{
  factores: readonly FactorRiesgo[];
}>();

const ICONOS: Record<IconoFactor, Component> = {
  luna: IconoLuna,
  rombo: IconoRombo,
};
</script>

<template>
  <section class="factores">
    <h2 class="factores__titulo">Lo más importante hoy</h2>
    <p class="factores__subtitulo">Variables que más pueden influir en el riesgo de hoy.</p>

    <ul class="factores__lista">
      <li v-for="factor in factores" :key="factor.id" class="factor">
        <span class="factor__caja">
          <component :is="ICONOS[factor.icono]" class="factor__glifo" />
        </span>

        <span class="factor__texto">
          <span class="factor__titulo">{{ factor.titulo }}</span>
          <span class="factor__detalle">{{ factor.detalle }}</span>
        </span>

        <span class="factor__prioridad">{{ ETIQUETA_PRIORIDAD[factor.prioridad] }}</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.factores {
  padding: var(--faro-esp-18) var(--faro-esp-16);
  background: var(--faro-superficie);
  border-radius: var(--faro-radio-24);
  box-shadow: var(--faro-sombra-tarjeta);
}

.factores__titulo {
  font-size: var(--faro-fs-15);
  font-weight: 700;
  color: var(--faro-verde-profundo);
}

.factores__subtitulo {
  margin-top: var(--faro-esp-4);
  font-size: var(--faro-fs-12);
  color: var(--faro-gris-texto);
}

.factores__lista {
  display: flex;
  flex-direction: column;
  gap: var(--faro-esp-12);
  margin-top: var(--faro-esp-14);
}

.factor {
  display: flex;
  align-items: center;
  gap: var(--faro-esp-12);
}

.factor__caja {
  display: grid;
  flex: none;
  place-items: center;
  width: var(--faro-caja-icono);
  height: var(--faro-caja-icono);
  background: var(--faro-verde-icono-fondo);
  border-radius: var(--faro-radio-10);
  color: var(--faro-verde-icono);
}

.factor__glifo {
  width: var(--faro-icono-16);
  height: var(--faro-icono-16);
}

.factor__texto {
  display: flex;
  flex: 1;
  flex-direction: column;
  /* Deja que el bloque encoja antes que empujar la etiqueta fuera de la tarjeta. */
  min-width: 0;
}

.factor__titulo {
  font-size: var(--faro-fs-135);
  font-weight: 700;
  color: var(--faro-verde-titulo);
}

.factor__detalle {
  font-size: var(--faro-fs-12);
  color: var(--faro-gris-texto);
}

.factor__prioridad {
  flex: none;
  padding: var(--faro-esp-4) var(--faro-esp-9);
  font-size: var(--faro-fs-11);
  font-weight: 700;
  color: var(--faro-alerta-texto);
  background: var(--faro-alerta-fondo);
  border-radius: var(--faro-radio-pastilla);
}
</style>
