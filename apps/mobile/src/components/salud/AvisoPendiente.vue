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

/**
 * Lo que dice el aviso.
 *
 * Antes decía "Tienes un formulario este día", que era exacto mientras el aviso
 * vivía en la columna, debajo del día que se estaba mirando: allí "este día" se
 * leía contra la fecha que había justo encima. Flotando sobre la pantalla ya no
 * tiene esa fecha al lado, así que la frase la nombra ella.
 *
 * El día concreto no se pierde: sigue en el `aria-label`, que es lo que lee un
 * lector de pantalla al llegar al botón.
 */
const TITULO = "Hoy no has completado el cuestionario diario";

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
      <span class="aviso__titulo">{{ TITULO }}</span>
    </span>

    <IconoChevron class="aviso__chevron" />
  </button>
</template>

<style scoped>
/*
 * El aviso entero es el botón, y ahora además flota.
 *
 * Antes era una tarjeta más de la columna: aparecía en su sitio, entre las
 * otras, y para verla había que haber llegado hasta ahí desplazándose. Es la
 * única acción de la pantalla —todo lo demás informa— y era la única que se
 * podía perder de vista.
 *
 * `fixed` en la esquina de abajo a la derecha: se queda donde cae el pulgar, no
 * se mueve con el contenido y no le quita sitio a ninguna tarjeta. Lo que sí le
 * quita es la esquina, así que Salud le suma ese hueco a su acolchado de abajo
 * mientras el aviso está —ver `pantalla__contenido--con-aviso`.
 *
 * No lleva `v-if` propio: aparece porque quien lo pinta decide que hay
 * formulario pendiente, y desaparece con el envío. (El comentario vive aquí y
 * no en la plantilla porque un comentario suelto en la raíz convierte el
 * componente en fragmento y deja de heredar clases y estilos.)
 *
 * Fuera de las bandas a propósito: el naranja es siempre el mismo porque no
 * habla del riesgo del día, sino de algo que le falta por hacer al usuario. Si
 * cambiara de color con la banda, se leería como parte del estado.
 *
 * El `z-index` lo deja por encima del contenido y por debajo de los diálogos
 * —el modal va en 10—: con el cuestionario abierto, el aviso que lleva a él no
 * tiene nada que hacer flotando sobre la hoja.
 */
.aviso {
  position: fixed;
  right: max(var(--blubathon-esp-16), env(safe-area-inset-right, 0px));
  bottom: calc(var(--blubathon-esp-16) + env(safe-area-inset-bottom, 0px));
  z-index: 5;
  display: flex;
  align-items: center;
  gap: var(--blubathon-esp-12);
  /* Del ancho de su texto, no del de la pantalla: es un globo, no una barra.
     El tope lo deja envolver en dos renglones en un teléfono y no cruzar la
     ventana entera en escritorio. */
  width: max-content;
  max-width: min(20rem, calc(100vw - var(--blubathon-esp-24) * 2));
  padding: var(--blubathon-esp-12);
  text-align: left;
  background: var(--blubathon-aviso-fondo);
  border-radius: var(--blubathon-radio-24);
  /* Elevación 2, la más alta: es lo único que flota de verdad sobre la página.
     El filete claro lo despega del fondo cuando cae sobre una burbuja. */
  box-shadow:
    0 0 0 1px oklch(1 0 0 / 0.55),
    var(--blubathon-elev-2);
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

/* Un punto por debajo de lo que medía en la columna: la frase es más larga que
   la de antes y, flotando, tiene menos ancho donde caber. */
.aviso__titulo {
  font-size: var(--blubathon-fs-135);
  font-weight: 700;
  line-height: 1.3;
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

.aviso--flotante {
  animation-name: flotante;
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

/*
 * El salto. Ocupa el primer 40% del ciclo y el 60% restante es descanso: con
 * los 5s de siempre son dos segundos de movimiento y tres de quietud, así que
 * se ve saltar sin que haya nada agitándose en la esquina mientras se lee.
 *
 * El rebote es la mitad de alto que el salto —7px y 3px—, que es lo que lo
 * separa de un vaivén: un vaivén sube y baja lo mismo siempre, algo que salta
 * pierde altura al caer.
 */
@keyframes flotante {
  0%,
  24%,
  40%,
  100% {
    transform: translateY(0);
  }

  12% {
    transform: translateY(-7px);
  }

  32% {
    transform: translateY(-3px);
  }
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
  .aviso.aviso--flotante,
  .aviso.aviso--pulso,
  .aviso.aviso--aparicion,
  .aviso.aviso--deslizamiento {
    animation: none;
  }
}
</style>
