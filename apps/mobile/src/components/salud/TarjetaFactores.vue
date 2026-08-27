<script setup lang="ts">
import { BLUBATHON_TEXTS_ES } from "@blubathon/contract/texts";
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
      {{ BLUBATHON_TEXTS_ES.emptyEs }}
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

        <span class="factor__prioridad" :class="`factor__prioridad--${factor.prioridad}`">
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
  padding: var(--blubathon-esp-18) var(--blubathon-esp-16);
  background: var(--blubathon-superficie);
  border-radius: var(--blubathon-radio-24);
  box-shadow: var(--blubathon-sombra-tarjeta);
}

.factores__titulo {
  font-size: var(--blubathon-fs-17);
  font-weight: 700;
  color: var(--blubathon-marca-profundo);
}

.factores__subtitulo {
  margin-top: var(--blubathon-esp-4);
  font-size: var(--blubathon-fs-125);
  color: var(--blubathon-gris-texto);
}

.factores__lista {
  margin-top: var(--blubathon-esp-10);
}

.factores__vacio {
  margin-top: var(--blubathon-esp-10);
  font-size: var(--blubathon-fs-125);
  color: var(--blubathon-gris-texto);
}

/*
 * Filete entre filas, no `gap`: separa igual y no dibuja una caja dentro de la
 * caja. Lo lleva la fila de abajo, así que ni la primera ni la última cortan
 * el acolchado de la tarjeta.
 */
.factor {
  display: flex;
  align-items: center;
  gap: var(--blubathon-esp-12);
  padding-block: var(--blubathon-esp-10);
}

.factor + .factor {
  border-top: 1px solid var(--blubathon-linea);
}

.factor__caja {
  display: grid;
  flex: none;
  place-items: center;
  width: var(--blubathon-caja-icono);
  height: var(--blubathon-caja-icono);
  background: var(--blubathon-marca-icono-fondo);
  border-radius: var(--blubathon-radio-10);
  color: var(--blubathon-marca-icono);
}

.factor__glifo {
  width: var(--blubathon-icono-16);
  height: var(--blubathon-icono-16);
}

.factor__texto {
  display: flex;
  flex: 1;
  flex-direction: column;
  /* Deja que el bloque encoja antes que empujar la etiqueta fuera de la tarjeta. */
  min-width: 0;
}

.factor__titulo {
  font-size: var(--blubathon-fs-135);
  font-weight: 700;
  color: var(--blubathon-marca-titulo);
}

.factor__detalle {
  font-size: var(--blubathon-fs-125);
  color: var(--blubathon-gris-texto);
}

/*
 * La prioridad es una señal de severidad, no del día: por eso su color no entra
 * en las bandas y es siempre el mismo. El punto la hace reconocible de un
 * vistazo sin subir el peso del texto.
 *
 * Los dos niveles usan los dos pares que ya existían —el de la alerta y el del
 * aviso pendiente—, así que "alta" se ve exactamente igual que antes.
 */
.factor__prioridad {
  display: flex;
  flex: none;
  align-items: center;
  gap: var(--blubathon-esp-6);
  padding: var(--blubathon-esp-4) var(--blubathon-esp-9);
  font-size: var(--blubathon-fs-11);
  font-weight: 700;
  color: var(--blubathon-critica-alta-texto);
  background: var(--blubathon-critica-alta-fondo);
  border-radius: var(--blubathon-radio-pastilla);
}

.factor__prioridad--media {
  color: var(--blubathon-critica-media-texto);
  background: var(--blubathon-critica-media-fondo);
}

.factor__punto {
  width: var(--blubathon-esp-6);
  height: var(--blubathon-esp-6);
  background: currentcolor;
  border-radius: 50%;
}
</style>
