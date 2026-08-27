<script setup lang="ts">
import { computed, type CSSProperties } from "vue";

import IconoChevron from "@/components/icons/IconoChevron.vue";
import IconoPortapapeles from "@/components/icons/IconoPortapapeles.vue";
import {
  ANIMACION_AVISO_POR_DEFECTO,
  CLASE_ANIMACION,
  DURACION_AVISO,
  VARIABLE_DURACION,
  normalizarDuracion,
  type AnimacionAviso,
} from "@/theme/tokens";

const props = withDefaults(
  defineProps<{
    /** Día ya formateado y en minúscula: "martes 25". Solo para el `aria-label`. */
    dia: string;
    animar?: boolean;
    animacion?: AnimacionAviso;
    /** Segundos. Se recorta al rango 3-9 con paso 0.5. */
    duracion?: number;
  }>(),
  {
    animar: true,
    animacion: ANIMACION_AVISO_POR_DEFECTO,
    duracion: DURACION_AVISO.porDefecto,
  },
);

defineEmits<{
  abrirFormulario: [];
}>();

const clases = computed<string[]>(() =>
  props.animar ? ["aviso--animado", CLASE_ANIMACION[props.animacion]] : [],
);

const estilo = computed<CSSProperties>(() => ({
  [VARIABLE_DURACION]: `${normalizarDuracion(props.duracion)}s`,
}));

const etiquetaBoton = computed(() => `Abrir formulario pendiente del ${props.dia}`);
</script>

<template>
  <button
    type="button"
    class="aviso"
    :class="clases"
    :style="estilo"
    :aria-label="etiquetaBoton"
    @click="$emit('abrirFormulario')"
  >
    <span class="aviso__insignia" aria-hidden="true">
      <IconoPortapapeles class="aviso__icono" />
    </span>

    <span class="aviso__texto">
      <span class="aviso__etiqueta">Pendiente</span>
      <span class="aviso__titulo">Tienes un formulario este día</span>
    </span>

    <IconoChevron class="aviso__chevron" />
  </button>
</template>

<style scoped>
/*
 * El aviso entero es el botón. Antes el texto quedaba suelto sobre el fondo de
 * la página y solo se pulsaba un cuadrado naranja al lado: había que adivinar
 * que las dos cosas eran la misma. Ahora es una pieza sola, con su superficie,
 * y se pulsa donde se lee. (El comentario vive aquí y no en la plantilla porque
 * un comentario suelto en la raíz convierte el componente en fragmento y deja
 * de heredar clases y estilos.)
 *
 * Fuera de las bandas a propósito: el naranja es siempre el mismo porque no
 * habla del riesgo del día, sino de algo que le falta por hacer al usuario. Si
 * cambiara de color con la banda, se leería como parte del estado.
 *
 * Es la única acción de la pantalla, así que es lo único en elevación 2. El
 * resto del contenido informa; esto pide que hagas algo.
 */
.aviso {
  display: flex;
  align-items: center;
  gap: var(--blubathon-esp-14);
  width: 100%;
  padding: var(--blubathon-esp-12);
  text-align: left;
  background: var(--blubathon-aviso-fondo);
  border-radius: var(--blubathon-radio-24);
  box-shadow: var(--blubathon-elev-2);
}

.aviso:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-aviso-titulo);
  outline-offset: var(--blubathon-foco-offset);
}

.aviso__insignia {
  display: grid;
  flex: none;
  place-items: center;
  width: var(--blubathon-toque);
  height: var(--blubathon-toque);
  color: #fff;
  background: var(--blubathon-aviso-insignia);
  border-radius: var(--blubathon-radio-18);
}

.aviso__icono {
  width: var(--blubathon-icono-26);
  height: var(--blubathon-icono-26);
}

.aviso__texto {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: var(--blubathon-esp-4);
  min-width: 0;
}

.aviso__etiqueta {
  font-size: var(--blubathon-fs-11);
  font-weight: 700;
  letter-spacing: var(--blubathon-track-012);
  text-transform: uppercase;
  color: var(--blubathon-aviso-etiqueta);
}

.aviso__titulo {
  font-size: var(--blubathon-fs-155);
  font-weight: 700;
  line-height: 1.25;
  color: var(--blubathon-aviso-titulo);
}

.aviso__chevron {
  flex: none;
  width: var(--blubathon-icono-16);
  height: var(--blubathon-icono-16);
  color: var(--blubathon-aviso-chevron);
}

.aviso--animado {
  animation-duration: var(--blubathon-dur);
  animation-timing-function: ease-in-out;
  animation-iteration-count: infinite;
}

.aviso--pulso {
  animation-name: pulso;
}

.aviso--aparicion {
  animation-name: aparicion;
}

.aviso--deslizamiento {
  animation-name: deslizamiento;
}

/* Con la pieza a todo el ancho el pulso tiene que ser más corto que cuando era
   un botón suelto: el mismo 1.4% de escala en 342px se convierte en 5px de
   vaivén y se vuelve ruido. */
@keyframes pulso {
  0%,
  100% {
    transform: translateY(0) scale(1);
  }

  50% {
    transform: translateY(-2px) scale(1.006);
  }
}

@keyframes aparicion {
  0%,
  100% {
    opacity: 0.86;
  }

  50% {
    opacity: 1;
  }
}

@keyframes deslizamiento {
  0%,
  100% {
    transform: translateY(0);
  }

  50% {
    transform: translateY(-4px);
  }
}

/* Manda sobre `animar: true`. Dos clases ganan por especificidad: sin
   `!important`. */
@media (prefers-reduced-motion: reduce) {
  .aviso.aviso--animado,
  .aviso.aviso--pulso,
  .aviso.aviso--aparicion,
  .aviso.aviso--deslizamiento {
    animation: none;
  }
}
</style>
