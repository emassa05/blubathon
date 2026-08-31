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

/**
 * Lo que dice el aviso.
 *
 * Una sola línea, y corta: ahora el aviso es una pastilla con un disco encima,
 * y esa forma solo se sostiene mientras el texto quepa en un renglón. La frase
 * anterior —"Hoy no has completado el cuestionario diario"— describía el estado
 * en tres renglones; esta avisa en uno.
 *
 * Empieza por "Hoy" porque el aviso flota sobre la pantalla y no tiene ninguna
 * fecha al lado que lo sitúe. Y lleva exclamación porque es lo único de la
 * pantalla que pide algo: el resto informa.
 *
 * El día concreto no se pierde: sigue en el `aria-label`, que es lo que lee un
 * lector de pantalla al llegar al botón.
 */
const TITULO = "¡Hoy te falta el cuestionario!";

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
    <span class="aviso__pastilla">{{ TITULO }}</span>

    <span class="aviso__insignia" aria-hidden="true">
      <IconoPortapapeles class="aviso__icono" />
    </span>
  </button>
</template>

<style scoped>
/*
 * El aviso entero es el botón, y flota anclado en la esquina de abajo a la
 * derecha.
 *
 * Antes era una tarjeta más de la columna: aparecía en su sitio, entre las
 * otras, y para verla había que haber llegado hasta ahí desplazándose. Es la
 * única acción de la pantalla —todo lo demás informa— y era la única que se
 * podía perder de vista.
 *
 * `fixed` en esa esquina: se queda donde cae el pulgar, no se mueve con el
 * contenido y no le quita sitio a ninguna tarjeta. Lo que sí le quita es la
 * esquina, así que Salud le suma ese hueco a su acolchado de abajo mientras el
 * aviso está —ver `pantalla__contenido--con-aviso`.
 *
 * El botón en sí no se ve: no tiene fondo ni sombra. Lo que se ve son sus dos
 * piezas, la pastilla y el disco, y quien manda en la altura es el disco, que
 * es la pieza alta. Por eso el `bottom` mide desde el disco y no desde la
 * pastilla, que queda flotando por encima de ese borde.
 *
 * El margen derecho lo toma el disco, que es lo que más sobresale por ese lado:
 * es su borde el que se queda a 16px de la pantalla, y la pastilla acaba antes.
 *
 * No lleva `v-if` propio: aparece porque quien lo pinta decide que hay
 * formulario pendiente, y desaparece con el envío. (El comentario vive aquí y
 * no en la plantilla porque un comentario suelto en la raíz convierte el
 * componente en fragmento y deja de heredar clases y estilos.)
 *
 * El `z-index` lo deja por encima del contenido y por debajo de los diálogos
 * —el modal va en 10—: con el cuestionario abierto, el aviso que lleva a él no
 * tiene nada que hacer flotando sobre la hoja.
 */
.aviso {
  position: fixed;
  right: max(var(--blubathon-esp-16), env(safe-area-inset-right, 0px));
  /* `max` y no una suma, igual que el margen derecho de aquí arriba: en un
     teléfono con barra de gestos la suma apilaba los 34px del área segura
     encima de los 16 propios y la pastilla acababa flotando a media altura de
     la esquina. Lo que hace falta del área segura es no meterse debajo de la
     barra, no apartarse de ella. */
  bottom: max(var(--blubathon-esp-8), env(safe-area-inset-bottom, 0px));
  z-index: 5;
  display: flex;
  align-items: center;
  /* Del ancho de su texto, no del de la pantalla: es un globo, no una barra.
     El tope es la ventana menos los dos márgenes; si el texto no cabe, envuelve
     dentro de la pastilla y el disco sigue centrado sobre ella. */
  width: max-content;
  max-width: calc(100vw - var(--blubathon-esp-16) * 2);
  padding: 0;
  text-align: left;
  background: none;
  border: 0;
}

/*
 * La pastilla. Fuera de las bandas a propósito: el crema y el marrón son
 * siempre los mismos porque no hablan del riesgo del día, sino de algo que le
 * falta por hacer al usuario. Si cambiaran de color con la banda, se leerían
 * como parte del estado.
 *
 * Acolchado asimétrico: por la izquierda es el aire de siempre, y por la
 * derecha se le suma entero el saliente del disco, porque esa mitad de la
 * pastilla la tapa el disco y el texto no puede meterse debajo.
 *
 * Elevación 2, la más alta: es lo único que flota de verdad sobre la página.
 * El filete claro la despega del fondo cuando cae sobre una burbuja.
 */
.aviso__pastilla {
  min-width: 0;
  padding: var(--blubathon-esp-8) 0 var(--blubathon-esp-8) var(--blubathon-esp-20);
  padding-right: calc(var(--blubathon-aviso-saliente) + var(--blubathon-esp-14));
  font-size: var(--blubathon-fs-135);
  font-weight: 800;
  line-height: 1.3;
  color: var(--blubathon-aviso-titulo);
  background: var(--blubathon-aviso-fondo);
  border-radius: var(--blubathon-radio-pastilla);
  box-shadow:
    0 0 0 1px oklch(1 0 0 / 0.55),
    var(--blubathon-elev-2);
}

/*
 * El disco, a caballo del extremo derecho de la pastilla.
 *
 * Se mete media anchura dentro con el margen negativo, así que su centro cae
 * justo en el borde derecho de la pastilla: por dentro le tapa el remate
 * redondo entero, y por fuera asoma la otra media. Como es más alto que la
 * pastilla y los dos van centrados, sobresale también por arriba y por abajo.
 *
 * `z-index` porque el orden del DOM lo pondría debajo: va después, pero el
 * apilado en un contenedor flex lo decide el orden de pintado y sin esto el
 * margen negativo lo metería por detrás del crema.
 */
.aviso__insignia {
  position: relative;
  z-index: 1;
  display: grid;
  flex: none;
  place-items: center;
  width: var(--blubathon-aviso-disco);
  height: var(--blubathon-aviso-disco);
  margin-left: calc(var(--blubathon-aviso-saliente) * -1);
  color: #fff;
  background: var(--blubathon-aviso-insignia);
  border-radius: 50%;
  box-shadow: var(--blubathon-elev-2);
}

.aviso__icono {
  width: var(--blubathon-icono-26);
  height: var(--blubathon-icono-26);
}

/* El foco rodea las dos piezas, que es lo que se pulsa: el botón entero. Con la
   pastilla y el disco de radios distintos, el anillo se dibuja sobre la caja
   del botón, y el radio de pastilla es el que menos se despega de la silueta. */
.aviso:focus-visible {
  border-radius: var(--blubathon-radio-pastilla);
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-aviso-titulo);
  outline-offset: var(--blubathon-foco-offset);
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
