<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId } from "vue";

import IconoCerrar from "@/components/icons/IconoCerrar.vue";
import { useDialogo } from "@/composables/useDialogo";

const props = withDefaults(
  defineProps<{
    titulo: string;
    /** Línea corta encima del título: de qué es este diálogo. */
    sobretitulo?: string;
    etiquetaCerrar?: string;
    /**
     * `hoja` sube desde abajo y se apoya en el borde inferior, que es donde
     * llega el pulgar; en pantalla ancha se centra. `centrado` nace en el centro
     * en las dos densidades: es para lo que hay que mirar, no para lo que hay
     * que alcanzar.
     */
    variante?: "hoja" | "centrado";
    /**
     * `false` lo vuelve obligatorio: sin aspa, sin velo que cierre al pulsarlo
     * y sin `Esc`. La única salida es contestar.
     */
    cerrable?: boolean;
    /** Una hoja abierta sobre otra sube un plano. 0 es el de la página. */
    nivel?: number;
  }>(),
  {
    sobretitulo: "",
    etiquetaCerrar: "Cerrar",
    variante: "hoja",
    cerrable: true,
    nivel: 0,
  },
);

const emitir = defineEmits<{ cerrar: [] }>();

const contenedor = ref<HTMLElement | null>(null);
const idTitulo = useId();

/*
 * Lo que tarda en entrar y en irse.
 *
 * Viven aquí y no en `tokens.css` porque no son solo estilo: la de salida es
 * también lo que se espera antes de avisar al padre de que ya puede desmontar
 * el diálogo. Si fueran dos cifras en dos sitios podrían separarse, y entonces
 * el diálogo desaparecería a medio irse, o se quedaría un rato invisible
 * tapando la pantalla. El CSS las recibe por variable, de aquí.
 */
const MS_ENTRADA = 300;
const MS_SALIDA = 210;

/*
 * El movimiento lo lleva el componente, no `<Transition>`.
 *
 * `<Transition>` decide cuánto dura una transición leyendo las propiedades
 * `transition` del **elemento raíz** que aparece y desaparece —aquí el velo—, y
 * lo que se mueve no es el velo: es la hoja, que cuelga de él. Con el velo sin
 * transición propia, Vue daba la salida por terminada en el mismo fotograma en
 * que empezaba y desmontaba el diálogo antes de que la hoja se hubiera movido:
 * el cierre no se veía. `:duration` lo tapa, pero deja el movimiento atado a un
 * ciclo de clases que no se puede observar ni probar sin cronómetro.
 *
 * Así que la hoja no depende de eso. `dentro` es un booleano de este
 * componente: falso mientras está fuera de la pantalla, verdadero cuando ocupa
 * su sitio. El CSS anima la diferencia entre los dos estados y el mismo valor
 * sirve para entrar y para salir.
 */
const dentro = ref(false);
let temporizador: ReturnType<typeof setTimeout> | null = null;

onMounted(async () => {
  await nextTick();
  /*
   * Un reflujo forzado antes de pedir el sitio.
   *
   * La hoja se acaba de pintar fuera de la pantalla, y sin obligar al navegador
   * a calcular ese estado de partida, el cambio a `dentro` se agrupa con el
   * primer pintado y no queda nada entre medias que animar: la hoja aparecería
   * ya puesta. Leer `offsetHeight` es lo que fija el punto de salida.
   */
  void contenedor.value?.offsetHeight;
  dentro.value = true;
});

const duraciones = computed(() => ({
  "--blubathon-dur-entrada": `${MS_ENTRADA}ms`,
  "--blubathon-dur-salida": `${MS_SALIDA}ms`,
}));

useDialogo(contenedor, pedirCierre, { cerrarConEsc: () => props.cerrable });

/*
 * Cerrar no desmonta: primero la hoja se va, y solo cuando ha terminado se
 * avisa al padre, que es quien la quita del DOM. Sin ese paso intermedio el
 * `v-if` de fuera la arrancaría antes de que la salida tuviera nada que animar.
 */
function pedirCierre(): void {
  // Ya se está yendo: una segunda pulsación no arranca un segundo cierre.
  if (!props.cerrable || temporizador !== null) return;
  dentro.value = false;
  temporizador = setTimeout(() => emitir("cerrar"), MS_SALIDA);
}

onBeforeUnmount(() => {
  if (temporizador !== null) clearTimeout(temporizador);
});
</script>

<template>
  <!--
    Sin `Teleport`: no hay ningún ancestro con `transform`, `filter` ni
    `contain` que rompa un `position: fixed`, así que el diálogo funciona donde
    se declara y las pruebas pueden montarlo sin buscarlo por `document.body`.
  -->
  <div
    class="velo"
    :class="[`velo--${variante}`, { 'velo--obligatorio': !cerrable, 'velo--dentro': dentro }]"
    :style="{ zIndex: 10 + nivel * 10, ...duraciones }"
  >
    <!--
        El velo también cierra al pulsarlo, y para eso es un botón de verdad: con
        nombre accesible y fuera del orden de tabulación, porque el control que se
        recorre con el teclado es la aspa de la cabecera, y `Esc` hace lo mismo.

        En un diálogo obligatorio no hay tal botón. No es un botón desactivado:
        es que pulsar fuera no es una salida, y un control que no lleva a ningún
        sitio no debería anunciarse.
      -->
    <button
      v-if="cerrable"
      type="button"
      class="velo__fondo"
      tabindex="-1"
      :aria-label="etiquetaCerrar"
      @click="pedirCierre"
    ></button>
    <div v-else class="velo__fondo" aria-hidden="true"></div>

    <div
      ref="contenedor"
      class="dialogo"
      :class="{ 'dialogo--portada': !!$slots.portada }"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="idTitulo"
      tabindex="-1"
    >
      <header class="dialogo__cabecera" :class="{ 'dialogo__cabecera--portada': !!$slots.portada }">
        <!--
          Con portada, la cabecera **es** la portada: los rótulos se dibujan
          dentro de ella, que es donde el diseño los pone. Por eso recibe el id
          del título —el `role="dialog"` sigue tomando su nombre de ese `h2`, lo
          pinte quien lo pinte— y por eso no se dibujan también aquí: se leerían
          dos veces. El aspa se queda flotando encima, en el sitio de siempre.
        -->
        <div v-if="$slots.portada" class="dialogo__portada">
          <slot name="portada" :id-titulo="idTitulo" />
        </div>

        <template v-else>
          <span
            v-if="variante === 'hoja' && cerrable"
            class="dialogo__asa"
            aria-hidden="true"
          ></span>

          <div class="dialogo__rotulos">
            <!-- El "(?)" va con el sobretítulo, que es el que nombra de qué es
                 el diálogo, y no con el título, que aquí es la fecha. La ayuda
                 explica el cuestionario, no el martes. -->
            <p v-if="sobretitulo" class="dialogo__sobretitulo">
              {{ sobretitulo }}
              <slot name="ayuda" />
            </p>
            <h2 :id="idTitulo" class="dialogo__titulo">{{ titulo }}</h2>
          </div>
        </template>

        <button
          v-if="cerrable"
          type="button"
          class="dialogo__cerrar"
          :aria-label="etiquetaCerrar"
          @click="pedirCierre"
        >
          <IconoCerrar class="dialogo__aspa" />
        </button>
      </header>

      <!-- Colapsa si no hay contenido, igual que el pie: un diálogo que solo
             es una pregunta y dos botones no lleva una franja vacía en medio. -->
      <div v-if="$slots.default" class="dialogo__cuerpo">
        <slot />
      </div>

      <footer v-if="$slots.pie" class="dialogo__pie">
        <slot name="pie" />
      </footer>
    </div>
  </div>
</template>

<style scoped>
/*
 * En móvil el diálogo sube desde abajo y se queda pegado al borde inferior: es
 * donde llega el pulgar y es el gesto que ya conoce cualquiera. En pantalla
 * ancha eso no significa nada, así que se centra y se recorta a un ancho de
 * lectura. Es el mismo componente; lo único que cambia es dónde se apoya.
 */
.velo {
  position: fixed;
  inset: 0;
  z-index: 10;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.velo__fondo {
  position: absolute;
  inset: 0;
  background: var(--blubathon-velo);
  cursor: default;
}

.dialogo {
  position: relative;
  display: flex;
  flex-direction: column;
  width: 100%;
  /* La misma columna que el resto de la aplicación: en un teléfono ocupa todo
     el ancho y en una ventana intermedia no se estira más que la pantalla. */
  max-width: var(--blubathon-ancho-max);
  max-height: 92dvh;
  background: var(--blubathon-fondo-final);
  border-radius: var(--blubathon-radio-32) var(--blubathon-radio-32) 0 0;
  box-shadow: var(--blubathon-elev-dialogo);
}

.dialogo:focus-visible {
  outline: none;
}

/*
 * La cabecera se queda arriba mientras el cuerpo se desplaza: en un cuestionario
 * de dieciocho preguntas, saber de qué día es no puede depender de haber
 * llegado al principio.
 */
.dialogo__cabecera {
  position: relative;
  padding: var(--blubathon-esp-18) var(--blubathon-esp-16) var(--blubathon-esp-14);
  background: var(--blubathon-superficie);
  border-radius: var(--blubathon-radio-32) var(--blubathon-radio-32) 0 0;
  border-bottom: 1px solid var(--blubathon-linea);
}

/* Con portada la cabecera es la portada y nada más: el acolchado, los rótulos y
   el fondo son suyos. */
.dialogo__cabecera--portada {
  padding: 0;
  border-bottom: 0;
}

/* Las esquinas de arriba son las de la hoja, y la portada va a sangre: sin
   recortarla aquí, su fondo asomaría por fuera del radio. */
.dialogo__portada {
  overflow: hidden;
  border-radius: var(--blubathon-radio-32) var(--blubathon-radio-32) 0 0;
}

/*
 * Y la hoja llega más arriba. La portada se come lo que antes era una cabecera
 * de dos líneas, y el formulario es lo que tiene que quedarse con el alto: sin
 * esto, añadir la cara y la fecha se pagaba en preguntas que hay que desplazar.
 */
.dialogo--portada {
  max-height: 96dvh;
  /*
   * Y una sola superficie. Sin portada el cuerpo es el color de la página y el
   * contenido va en tarjetas, que es lo que hace un diálogo con secciones. Con
   * portada no hay secciones: hay una cabecera de color y debajo un formulario,
   * así que el cuerpo es del mismo blanco que ese formulario y no se ve un
   * segundo plano por detrás.
   */
  background: var(--blubathon-superficie);
}

.dialogo--portada .dialogo__cuerpo {
  background: var(--blubathon-superficie);
}

/*
 * Y sin filete sobre el pie: el cuerpo y el pie son la misma superficie blanca,
 * así que una raya entre los dos solo dibujaba un borde donde no hay ninguno.
 */
.dialogo--portada .dialogo__pie {
  border-top: 0;
}

/* El asa no se arrastra: dice que esto sube y baja, no que sea una página. */
.dialogo__asa {
  position: absolute;
  top: var(--blubathon-esp-8);
  left: 50%;
  width: 38px;
  height: 4px;
  background: var(--blubathon-punto-inactivo);
  border-radius: var(--blubathon-radio-pastilla);
  transform: translateX(-50%);
}

/* El hueco de la derecha es el del aspa, que ya no es un hermano de fila sino
   una pieza flotante: sin él, un título largo se metería por debajo. */
.dialogo__rotulos {
  min-width: 0;
  padding-right: var(--blubathon-toque);
}

.dialogo__sobretitulo {
  display: flex;
  align-items: center;
  font-size: var(--blubathon-fs-11);
  font-weight: 700;
  letter-spacing: var(--blubathon-track-012);
  text-transform: uppercase;
  color: var(--blubathon-gris-texto);
}

.dialogo__titulo {
  margin-top: var(--blubathon-esp-4);
  font-size: var(--blubathon-fs-17);
  font-weight: 700;
  color: var(--blubathon-marca-profundo);
}

.dialogo__cerrar {
  position: absolute;
  top: var(--blubathon-esp-8);
  right: var(--blubathon-esp-10);
  display: grid;
  place-items: center;
  width: var(--blubathon-toque);
  height: var(--blubathon-toque);
  color: var(--blubathon-marca-texto);
  border-radius: 50%;
}

/* Sobre la portada el aspa va encima de un color, no de blanco: sin el vidrio
   detrás se pierde en cuanto la cara que salga sea clara. */
.dialogo__cabecera--portada .dialogo__cerrar {
  top: var(--blubathon-esp-10);
  right: var(--blubathon-esp-10);
  color: var(--blubathon-marca-profundo);
  background: var(--blubathon-vidrio);
}

.dialogo__cerrar:hover {
  background: var(--blubathon-fila-activa);
}

.dialogo__cerrar:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-foco-oscuro);
  outline-offset: var(--blubathon-foco-offset);
}

.dialogo__aspa {
  width: var(--blubathon-icono-16);
  height: var(--blubathon-icono-16);
}

.dialogo__cuerpo {
  flex: 1;
  /* Sin esto, un hijo de flex no baja de su alto de contenido y el diálogo
     entero crecería en vez de desplazarse por dentro. */
  min-height: 0;
  padding: var(--blubathon-esp-16);
  overflow-y: auto;
  /* Al llegar al final, la página de debajo no se lleva el desplazamiento. */
  overscroll-behavior: contain;
}

.dialogo__pie {
  padding: var(--blubathon-esp-12) var(--blubathon-esp-16)
    calc(var(--blubathon-esp-16) + env(safe-area-inset-bottom, 0px));
  background: var(--blubathon-superficie);
  border-top: 1px solid var(--blubathon-linea);
}

/*
 * La variante centrada. No es una hoja apoyada en el borde: flota, así que
 * lleva radio por los cuatro lados y un margen que la separa de los bordes de
 * la ventana incluso en un teléfono.
 */
.velo--centrado {
  align-items: center;
  padding: var(--blubathon-esp-20);
}

.velo--centrado .dialogo {
  max-width: var(--blubathon-ancho-dialogo);
  max-height: min(88dvh, 720px);
  border-radius: var(--blubathon-radio-32);
}

.velo--centrado .dialogo__cabecera {
  border-radius: var(--blubathon-radio-32) var(--blubathon-radio-32) 0 0;
}

.velo--centrado .dialogo__pie {
  padding-bottom: var(--blubathon-esp-16);
  border-radius: 0 0 var(--blubathon-radio-32) var(--blubathon-radio-32);
}

/*
 * Obligatorio: el velo es más denso que el de un diálogo que se puede cerrar.
 * No es decoración, es la diferencia que se ve sin leer nada —esto no es una
 * capa sobre la pantalla, es lo único que hay— y por eso el contexto de debajo
 * deja de reconocerse, que en cualquier otro diálogo sería un error.
 */
.velo--obligatorio .velo__fondo {
  background: var(--blubathon-velo-obligatorio);
}

/*
 * El movimiento.
 *
 * Dos estados y nada más: la hoja está fuera, o está dentro. `velo--dentro` lo
 * dice, lo pone este componente y el CSS anima la diferencia. No hay clases de
 * `<Transition>` de por medio, así que el estado se puede leer, afirmar en una
 * prueba y depurar mirando el DOM.
 *
 * La hoja **solo sube y baja**. No se desvanece: lo que se apaga es el fondo,
 * que es un hermano suyo. Antes la opacidad iba en el velo, que los envuelve a
 * los dos, y la hoja se apagaba a la vez que se movía —el recorrido no llegaba
 * a leerse y parecía un fundido.
 *
 * El diálogo centrado sí crece y se apaga en el sitio: no se apoya en ningún
 * borde, así que no hay ninguna dirección desde la que entrar.
 *
 * Las curvas no son simétricas a propósito: entra frenando largo, que es lo que
 * hace que parezca que algo pesado se posa, y sale más corta y más recta,
 * porque una salida lenta se lee como que la aplicación va lenta.
 */
.velo__fondo {
  opacity: 0;
  transition: opacity var(--blubathon-dur-salida) ease-in;
}

.velo--dentro .velo__fondo {
  opacity: 1;
  transition-duration: var(--blubathon-dur-entrada);
  transition-timing-function: var(--blubathon-curva-hoja);
}

/* Sale por debajo del borde de la ventana, no solo por el suyo: sin el `calc`
   se quedaba a la vista un canto de la hoja con el fondo ya apagado. */
.dialogo {
  transform: translateY(calc(100% + var(--blubathon-esp-32)));
  transition: transform var(--blubathon-dur-salida) ease-in;
}

.velo--dentro .dialogo {
  transform: none;
  transition-duration: var(--blubathon-dur-entrada);
  transition-timing-function: var(--blubathon-curva-hoja);
}

/* El centrado no tiene borde del que salir: crece y se apaga donde está. */
.velo--centrado .dialogo {
  opacity: 0;
  transform: scale(0.94);
  transition-property: transform, opacity;
}

.velo--centrado.velo--dentro .dialogo {
  opacity: 1;
  transform: none;
}

/*
 * Quien pide menos movimiento no pide menos diálogo: sigue apareciendo y
 * desapareciendo con una opacidad corta, que orienta igual, y lo que se quita
 * es el desplazamiento.
 *
 * Aquí la hoja **sí** se desvanece, y es el único sitio donde lo hace: sin
 * recorrido y sin fundido no quedaría transición ninguna, y la hoja aparecería
 * de golpe encima de la pantalla.
 */
@media (prefers-reduced-motion: reduce) {
  .dialogo,
  .velo--centrado .dialogo {
    opacity: 0;
    transform: none;
    transition-property: opacity;
  }

  .velo--dentro .dialogo,
  .velo--centrado.velo--dentro .dialogo {
    opacity: 1;
  }
}

/*
 * Ventana baja: la hoja llega casi arriba del todo y el acolchado se aprieta.
 * Con 92dvh de 390 px quedaban 359 para cabecera, cuerpo y pie, y el cuerpo
 * —que es el formulario— se quedaba en una tira de cien píxeles.
 */
@media (max-height: 520px) {
  .dialogo {
    max-height: 98dvh;
  }

  .dialogo__cabecera {
    padding-block: var(--blubathon-esp-10) var(--blubathon-esp-8);
  }

  .dialogo__cuerpo {
    padding-block: var(--blubathon-esp-10);
  }

  .velo--centrado {
    padding: var(--blubathon-esp-10);
  }
}

@media (min-width: 900px) {
  .velo {
    align-items: center;
    padding: var(--blubathon-esp-32);
  }

  .dialogo {
    max-width: var(--blubathon-ancho-dialogo);
    max-height: min(88dvh, 760px);
    border-radius: var(--blubathon-radio-32);
  }

  .dialogo__cabecera {
    padding: var(--blubathon-esp-20) var(--blubathon-esp-24) var(--blubathon-esp-16);
    border-radius: var(--blubathon-radio-32) var(--blubathon-radio-32) 0 0;
  }

  .dialogo__cerrar {
    top: var(--blubathon-esp-10);
    right: var(--blubathon-esp-18);
  }

  .dialogo__cabecera--portada .dialogo__cerrar {
    right: var(--blubathon-esp-10);
  }

  /* El asa es un gesto de móvil: en escritorio no dice nada. */
  .dialogo__asa {
    display: none;
  }

  .dialogo__cuerpo {
    padding: var(--blubathon-esp-20) var(--blubathon-esp-24);
  }

  .dialogo__pie {
    padding: var(--blubathon-esp-16) var(--blubathon-esp-24);
    border-radius: 0 0 var(--blubathon-radio-32) var(--blubathon-radio-32);
  }

  /* Ya centrada por el punto de corte: lo que sube desde abajo en un teléfono
     aparece en el sitio en escritorio, igual que la variante centrada. */
  .hoja-enter-from .dialogo,
  .hoja-leave-to .dialogo {
    transform: scale(0.96);
  }
}
</style>
