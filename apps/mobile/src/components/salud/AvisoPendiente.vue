<script setup lang="ts">
import { computed, type CSSProperties } from "vue";

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
  <div class="aviso" :class="clases" :style="estilo">
    <div class="aviso__texto">
      <p class="aviso__etiqueta">Pendiente</p>
      <p class="aviso__titulo">Tienes un formulario este día</p>
    </div>

    <button
      type="button"
      class="aviso__boton"
      :aria-label="etiquetaBoton"
      @click="$emit('abrirFormulario')"
    >
      <IconoPortapapeles class="aviso__icono" />
    </button>
  </div>
</template>

<style scoped>
.aviso {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--faro-esp-14);
}

.aviso__texto {
  text-align: right;
}

.aviso__etiqueta {
  font-size: var(--faro-fs-11);
  font-weight: 700;
  letter-spacing: var(--faro-track-012);
  text-transform: uppercase;
  color: var(--faro-naranja-etiqueta);
}

.aviso__titulo {
  font-size: var(--faro-fs-155);
  font-weight: 700;
  line-height: 1.3;
  color: var(--faro-naranja-titulo);
}

.aviso__boton {
  display: grid;
  flex: none;
  place-items: center;
  width: var(--faro-boton-aviso);
  height: var(--faro-boton-aviso);
  color: #fff;
  background: var(--faro-naranja-boton);
  border-radius: var(--faro-radio-18);
  box-shadow: var(--faro-sombra-boton);
}

.aviso__boton:focus-visible {
  outline: var(--faro-foco-grosor) solid var(--faro-foco-oscuro);
  outline-offset: var(--faro-foco-offset);
}

.aviso__icono {
  width: var(--faro-icono-26);
  height: var(--faro-icono-26);
}

.aviso--animado {
  animation-duration: var(--faro-dur);
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

@keyframes pulso {
  0%,
  100% {
    transform: translateY(0) scale(1);
  }

  50% {
    transform: translateY(-3px) scale(1.014);
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
    transform: translateY(-6px);
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
