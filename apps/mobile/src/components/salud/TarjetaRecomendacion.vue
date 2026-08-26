<script setup lang="ts">
import { computed } from "vue";

import type { Recomendacion } from "@/types/salud";

const props = defineProps<{
  recomendacion: Recomendacion;
}>();

const SOBRETITULO = "Recomendación de hoy";

const hayFoto = computed(() => props.recomendacion.imagen !== null);

const fondo = computed(() =>
  props.recomendacion.imagen === null
    ? {}
    : { backgroundImage: `url("${props.recomendacion.imagen}")` },
);
</script>

<template>
  <section class="recomendacion">
    <!-- TODO(spec): placeholder. La foto familiar a sangre la aporta el equipo;
         en cuanto `recomendacion.imagen` traiga una URL, esta capa la pinta. -->
    <div
      class="recomendacion__foto"
      :class="{ 'recomendacion__foto--placeholder': !hayFoto }"
      :style="fondo"
      aria-hidden="true"
    ></div>
    <div class="recomendacion__velo" aria-hidden="true"></div>

    <div class="recomendacion__texto">
      <h2 class="recomendacion__sobretitulo">{{ SOBRETITULO }}</h2>
      <p class="recomendacion__frase">{{ recomendacion.texto }}</p>
    </div>
  </section>
</template>

<style scoped>
.recomendacion {
  position: relative;
  display: flex;
  min-height: var(--faro-recomendacion-alto);
  overflow: hidden;
  border-radius: var(--faro-radio-26);
  box-shadow: var(--faro-sombra-tarjeta);
}

.recomendacion__foto,
.recomendacion__velo {
  position: absolute;
  inset: 0;
}

.recomendacion__foto {
  background-position: center;
  background-size: cover;
}

/* Marca deliberada de "aquí falta la foto": bandas suaves, nunca una foto de
   archivo que pueda colarse en una demo. */
.recomendacion__foto--placeholder {
  background-image: repeating-linear-gradient(
    135deg,
    oklch(0.62 0.06 168) 0 14px,
    oklch(0.55 0.07 168) 14px 28px
  );
}

.recomendacion__velo {
  background: var(--faro-velo-foto);
}

.recomendacion__texto {
  position: relative;
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: var(--faro-esp-6);
  justify-content: center;
  padding: var(--faro-esp-20);
  text-align: center;
}

.recomendacion__sobretitulo {
  font-size: var(--faro-fs-11);
  font-weight: 700;
  letter-spacing: var(--faro-track-014);
  text-transform: uppercase;
  color: rgb(255 255 255 / 0.88);
}

.recomendacion__frase {
  font-size: var(--faro-fs-17);
  font-weight: 600;
  line-height: 1.4;
  color: #fff;
  text-shadow: var(--faro-sombra-texto);
}
</style>
