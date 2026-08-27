<script setup lang="ts">
import { computed } from "vue";

import IconoEscudo from "@/components/icons/IconoEscudo.vue";
import IconoInfo from "@/components/icons/IconoInfo.vue";

const props = defineProps<{
  /** Riesgo de desregulación, 0-100. `null` cuando el modelo se abstiene. */
  riesgo: number | null;
  /** Confianza del modelo en ese riesgo, 0-100. `null` si no hay estimación. */
  confianza: number | null;
}>();

defineEmits<{
  masInfo: [];
}>();

const SOBRETITULO = "Riesgo de desregulación";

/** Sin cifra no se pone un cero: se dice que no la hay. */
const SIN_ESTIMACION = "—";

/** Una sola etiqueta legible: "Riesgo de desregulación: 18 por ciento". */
const etiqueta = computed(() =>
  props.riesgo === null
    ? `${SOBRETITULO}: sin estimación todavía`
    : `${SOBRETITULO}: ${props.riesgo} por ciento`,
);

const etiquetaInfo = computed(() => `Qué significa el ${SOBRETITULO.toLowerCase()}`);
</script>

<template>
  <header class="riesgo">
    <!-- Las piezas visuales van en aria-hidden para que no se lea
         "Riesgo de desregulación 18%" suelto: el nombre accesible lo pone el
         aria-label, en el encabezado y en el grupo que pide el diseño.
         `heading-has-content` solo mira el contenido de texto del encabezado,
         no su aria-label, y por eso hay que silenciarlo justo aquí. -->
    <!-- eslint-disable-next-line vuejs-accessibility/heading-has-content -->
    <h1 class="riesgo__titulo" :aria-label="etiqueta">
      <span class="riesgo__grupo" role="group" :aria-label="etiqueta">
        <span class="riesgo__linea">
          <span class="riesgo__sobretitulo" aria-hidden="true">{{ SOBRETITULO }}</span>

          <!-- TODO(spec): abrir el popup que explica la métrica. Por ahora solo
               existe el disparador; el contenido llega en otra pasada. -->
          <button
            type="button"
            class="riesgo__info"
            :aria-label="etiquetaInfo"
            @click="$emit('masInfo')"
          >
            <IconoInfo class="riesgo__glifo" />
          </button>
        </span>

        <!-- Sin espacios entre los dos tramos: la cifra y el signo son una sola
             palabra, y cualquier hueco aquí saldría también en el DOM. -->
        <span class="riesgo__cifra" aria-hidden="true"
          ><span>{{ riesgo ?? SIN_ESTIMACION }}</span
          ><span v-if="riesgo !== null" class="riesgo__porciento">%</span></span
        >
      </span>
    </h1>

    <!-- Sin estimación no hay confianza que dar: la pastilla desaparece en vez
         de mostrar un cero, que se leería como "confianza nula". -->
    <p v-if="confianza !== null" class="riesgo__confianza">
      <IconoEscudo class="riesgo__escudo" aria-hidden="true" />
      <span
        >Nivel de confianza <b class="riesgo__dato">{{ confianza }}%</b></span
      >
    </p>
  </header>
</template>

<style scoped>
.riesgo {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.riesgo__grupo {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.riesgo__linea {
  display: flex;
  align-items: center;
}

.riesgo__sobretitulo {
  font-size: var(--blubathon-fs-125);
  font-weight: 700;
  letter-spacing: var(--blubathon-track-014);
  text-transform: uppercase;
  color: var(--blubathon-texto-suave);
}

/*
 * El botón mide 44x44 de área táctil pero ocupa en la línea lo mismo que su
 * glifo más el hueco de 6: los dos márgenes negativos devuelven el acolchado
 * que el padding le robaría, así que el sobretítulo no se descoloca.
 */
.riesgo__info {
  display: grid;
  flex: none;
  place-items: center;
  min-width: var(--blubathon-toque);
  min-height: var(--blubathon-toque);
  margin-block: calc((var(--blubathon-toque) - var(--blubathon-icono-16)) / -2);
  margin-inline: calc(var(--blubathon-esp-6) - (var(--blubathon-toque) - var(--blubathon-icono-16)) / 2)
    calc((var(--blubathon-toque) - var(--blubathon-icono-16)) / -2);
  color: var(--blubathon-texto-suave);
  border-radius: var(--blubathon-radio-10);
}

.riesgo__info:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-foco-panel);
  outline-offset: var(--blubathon-foco-offset);
}

.riesgo__glifo {
  width: var(--blubathon-icono-16);
  height: var(--blubathon-icono-16);
}

.riesgo__cifra {
  margin-top: var(--blubathon-esp-4);
  font-size: var(--blubathon-fs-104);
  font-weight: 400;
  line-height: 1;
  letter-spacing: var(--blubathon-track-cifra);
  color: var(--blubathon-texto-fuerte);
}

/*
 * El signo, a la mitad de la cifra. Es lo que la deja crecer: con el `%` del
 * mismo cuerpo, el bloque se come el ancho y hay que encoger el número, que es
 * justo el dato que se venía a leer. En `em` para que siga a la cifra sea cual
 * sea su tamaño.
 */
.riesgo__porciento {
  font-size: 0.46em;
  letter-spacing: 0;
}

/*
 * La confianza va en pastilla, no suelta: es un dato secundario y en vidrio se
 * lee sobre cualquier punto del gradiente, sin depender de dónde caiga.
 */
.riesgo__confianza {
  display: flex;
  align-items: center;
  gap: var(--blubathon-esp-8);
  margin-top: var(--blubathon-esp-14);
  padding: var(--blubathon-esp-8) var(--blubathon-esp-14);
  font-size: var(--blubathon-fs-125);
  font-weight: 600;
  color: var(--blubathon-texto-suave);
  background: var(--blubathon-vidrio);
  border: 1px solid var(--blubathon-vidrio-borde);
  border-radius: var(--blubathon-radio-pastilla);
}

.riesgo__dato {
  font-weight: 700;
  color: var(--blubathon-texto-fuerte);
}

.riesgo__escudo {
  flex: none;
  width: var(--blubathon-icono-14);
  height: var(--blubathon-icono-14);
}
</style>
