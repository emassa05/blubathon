<script setup lang="ts">
import { FARO_TEXTS_ES } from "@faro/contract/texts";
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
    <!-- Lo que el formulario prioriza, no las causas del riesgo: el track
         visible es una tasa observada y no pondera predictores, así que
         atribuirle importancias sería afirmar algo que el modelo no calcula. -->
    <p class="factores__subtitulo">Lo que el formulario de hoy pregunta primero.</p>

    <p v-if="factores.length === 0" class="factores__vacio">
      {{ FARO_TEXTS_ES.emptyEs }}
    </p>

    <ul v-else class="factores__lista">
      <li v-for="factor in factores" :key="factor.id" class="factor">
        <span class="factor__caja">
          <component :is="ICONOS[factor.icono]" class="factor__glifo" />
        </span>

        <span class="factor__texto">
          <span class="factor__titulo">{{ factor.titulo }}</span>
          <span class="factor__detalle">{{ factor.detalle }}</span>
        </span>

        <span class="factor__prioridad">
          <span class="factor__punto" aria-hidden="true"></span>
          {{ ETIQUETA_PRIORIDAD[factor.prioridad] }}
        </span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
/*
 * Esta tarjeta es la que explica la cifra del panel, así que es la principal de
 * las tres: título un cuerpo por encima de las otras. La jerarquía se ve en el
 * título, no en el color ni en la sombra, que son iguales en todas.
 */
.factores {
  padding: var(--faro-esp-18) var(--faro-esp-16);
  background: var(--faro-superficie);
  border-radius: var(--faro-radio-24);
  box-shadow: var(--faro-sombra-tarjeta);
}

.factores__titulo {
  font-size: var(--faro-fs-17);
  font-weight: 700;
  color: var(--faro-verde-profundo);
}

.factores__subtitulo {
  margin-top: var(--faro-esp-4);
  font-size: var(--faro-fs-125);
  color: var(--faro-gris-texto);
}

.factores__lista {
  margin-top: var(--faro-esp-10);
}

.factores__vacio {
  margin-top: var(--faro-esp-10);
  font-size: var(--faro-fs-125);
  color: var(--faro-gris-texto);
}

/*
 * Filete entre filas, no `gap`: separa igual y no dibuja una caja dentro de la
 * caja. Lo lleva la fila de abajo, así que ni la primera ni la última cortan
 * el acolchado de la tarjeta.
 */
.factor {
  display: flex;
  align-items: center;
  gap: var(--faro-esp-12);
  padding-block: var(--faro-esp-10);
}

.factor + .factor {
  border-top: 1px solid var(--faro-linea);
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
  font-size: var(--faro-fs-125);
  color: var(--faro-gris-texto);
}

/*
 * La prioridad es una señal de severidad, no del día: por eso su color no entra
 * en las bandas y es siempre el mismo. El punto la hace reconocible de un
 * vistazo sin subir el peso del texto.
 */
.factor__prioridad {
  display: flex;
  flex: none;
  align-items: center;
  gap: var(--faro-esp-6);
  padding: var(--faro-esp-4) var(--faro-esp-9);
  font-size: var(--faro-fs-11);
  font-weight: 700;
  color: var(--faro-alerta-texto);
  background: var(--faro-alerta-fondo);
  border-radius: var(--faro-radio-pastilla);
}

.factor__punto {
  width: var(--faro-esp-6);
  height: var(--faro-esp-6);
  background: currentcolor;
  border-radius: 50%;
}
</style>
