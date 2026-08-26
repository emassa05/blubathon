<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  /** Porcentaje de bienestar, 0-100. */
  porcentaje: number;
}>();

const SOBRETITULO = "Bienestar de hoy";

/** Una sola etiqueta legible: "Bienestar de hoy: 86 por ciento". */
const etiqueta = computed(() => `${SOBRETITULO}: ${props.porcentaje} por ciento`);
</script>

<template>
  <header class="bienestar">
    <!-- Las piezas visuales van en aria-hidden para que no se lea
         "Bienestar de hoy 86%" suelto: el nombre accesible lo pone el
         aria-label, en el encabezado y en el grupo que pide el diseño.
         `heading-has-content` solo mira el contenido de texto del encabezado,
         no su aria-label, y por eso hay que silenciarlo justo aquí. -->
    <!-- eslint-disable-next-line vuejs-accessibility/heading-has-content -->
    <h1 class="bienestar__titulo" :aria-label="etiqueta">
      <span class="bienestar__grupo" role="group" :aria-label="etiqueta">
        <span class="bienestar__sobretitulo" aria-hidden="true">{{ SOBRETITULO }}</span>
        <span class="bienestar__cifra" aria-hidden="true">{{ porcentaje }}%</span>
      </span>
    </h1>
  </header>
</template>

<style scoped>
.bienestar {
  display: flex;
  justify-content: center;
  color: #fff;
  text-align: center;
}

.bienestar__grupo {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.bienestar__sobretitulo {
  font-size: var(--faro-fs-12);
  font-weight: 600;
  letter-spacing: var(--faro-track-014);
  text-transform: uppercase;
  opacity: 0.85;
}

.bienestar__cifra {
  font-size: var(--faro-fs-88);
  font-weight: 400;
  line-height: 1.05;
  letter-spacing: var(--faro-track-cifra);
}
</style>
