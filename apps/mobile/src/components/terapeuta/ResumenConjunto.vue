<script setup lang="ts">
import { computed } from "vue";

import { BANDAS_RIESGO, CLASE_BANDA, CORTE_ALTO, CORTE_MEDIO } from "@/theme/riesgo";
import type { ResumenConjunto } from "@/types/terapeuta";

const props = defineProps<{ conjunto: ResumenConjunto }>();

/**
 * Las bandas de mayor a menor, que es el orden en que se lee una lista de
 * prioridades. `BANDAS_RIESGO` va de menor a mayor porque es el orden natural
 * de la escala; aquí se invierte, y la abstención va al final: no es un cuarto
 * nivel, es la ausencia de nivel.
 */
const ORDEN = ["alto", "medio", "bajo", "desconocido"] as const;

const ETIQUETAS: Record<(typeof BANDAS_RIESGO)[number], string> = {
  alto: `Riesgo alto (≥ ${CORTE_ALTO}%)`,
  medio: `Riesgo medio (${CORTE_MEDIO}–${CORTE_ALTO}%)`,
  bajo: `Riesgo bajo (< ${CORTE_MEDIO}%)`,
  desconocido: "Sin estimación",
};

const filas = computed(() =>
  ORDEN.map((banda) => ({
    banda,
    etiqueta: ETIQUETAS[banda],
    cuenta: props.conjunto.porBanda[banda],
    // Proporción sobre la cartera, para la barra. Con cartera vacía es 0 y no
    // una división por cero.
    parte: props.conjunto.ninos === 0 ? 0 : props.conjunto.porBanda[banda] / props.conjunto.ninos,
  })),
);
</script>

<template>
  <section class="conjunto" aria-labelledby="conjunto-titulo">
    <h2 id="conjunto-titulo" class="conjunto__titulo">Conjunto de los niños</h2>

    <!--
      Cuentas, no medias. Un "riesgo medio de la cartera" promediaría líneas
      base personales, que es exactamente lo que el producto se niega a hacer:
      cada niño se compara consigo mismo, así que la única agregación honesta es
      contar cuántos hay en cada banda.
    -->
    <dl class="bandas">
      <div v-for="fila in filas" :key="fila.banda" class="banda" :class="CLASE_BANDA[fila.banda]">
        <dt class="banda__etiqueta">{{ fila.etiqueta }}</dt>
        <dd class="banda__cuenta">{{ fila.cuenta }}</dd>
        <dd class="banda__barra" aria-hidden="true">
          <span class="banda__relleno" :style="{ inlineSize: `${fila.parte * 100}%` }"></span>
        </dd>
      </div>
    </dl>
  </section>
</template>

<style scoped>
.conjunto {
  display: flex;
  flex-direction: column;
  gap: var(--blubathon-esp-14);
  padding: var(--blubathon-esp-18);
  background: var(--blubathon-superficie);
  border-radius: var(--blubathon-radio-24);
  box-shadow: var(--blubathon-elev-1);
}

.conjunto__titulo {
  font-size: var(--blubathon-fs-11);
  font-weight: 700;
  letter-spacing: var(--blubathon-track-014);
  text-transform: uppercase;
  color: var(--blubathon-gris-texto);
}

.bandas {
  display: flex;
  flex-direction: column;
  gap: var(--blubathon-esp-10);
}

/*
 * Cada fila es etiqueta, cuenta y barra. La barra es la que se compara de un
 * vistazo; la cuenta es la que se cita. Las dos, porque una barra sin número no
 * se puede repetir en voz alta y un número sin barra no se compara.
 */
.banda {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: var(--blubathon-esp-4) var(--blubathon-esp-10);
  align-items: baseline;
}

.banda__etiqueta {
  font-size: var(--blubathon-fs-12);
  color: var(--blubathon-marca-texto);
}

.banda__cuenta {
  font-size: var(--blubathon-fs-15);
  font-weight: 700;
  color: var(--blubathon-marca-profundo);
  font-variant-numeric: tabular-nums;
}

.banda__barra {
  grid-column: 1 / -1;
  height: var(--blubathon-esp-6);
  overflow: hidden;
  background: var(--blubathon-linea);
  border-radius: var(--blubathon-radio-pastilla);
}

.banda__relleno {
  display: block;
  height: 100%;
  /* El tono de la banda, heredado de la clase que lleva la fila: ningún color
     nuevo entra por esta pantalla. */
  background: var(--blubathon-onda-3, var(--blubathon-punto-inactivo));
  border-radius: inherit;
}
</style>
