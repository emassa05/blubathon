<script setup lang="ts">
import { computed, onBeforeUnmount, ref, useId } from "vue";

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
const MS_ENTRADA = 340;
const MS_SALIDA = 240;

/*
 * El diálogo se pinta abierto —de ahí el `appear` de la transición— y al
 * cerrarse no desaparece: primero se va, y solo cuando ha terminado avisa al
 * padre, que es quien lo desmonta. Sin ese paso intermedio el `v-if` de fuera
 * lo arrancaría del DOM antes de que la animación de salida tuviera nada que
 * animar.
 */
const visible = ref(true);
let temporizador: ReturnType<typeof setTimeout> | null = null;

const transicion = computed(() => (props.variante === "hoja" ? "hoja" : "centro"));

const duraciones = computed(() => ({
  "--faro-dur-entrada": `${MS_ENTRADA}ms`,
  "--faro-dur-salida": `${MS_SALIDA}ms`,
}));

useDialogo(contenedor, pedirCierre, { cerrarConEsc: () => props.cerrable });

function pedirCierre(): void {
  // Ya se está yendo: una segunda pulsación no arranca un segundo cierre.
  if (!props.cerrable || temporizador !== null) return;
  visible.value = false;
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
  <Transition :name="transicion" appear>
    <div
      v-if="visible"
      class="velo"
      :class="[`velo--${variante}`, { 'velo--obligatorio': !cerrable }]"
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
        role="dialog"
        aria-modal="true"
        :aria-labelledby="idTitulo"
        tabindex="-1"
      >
        <header class="dialogo__cabecera">
          <span
            v-if="variante === 'hoja' && cerrable"
            class="dialogo__asa"
            aria-hidden="true"
          ></span>

          <div class="dialogo__rotulos">
            <p v-if="sobretitulo" class="dialogo__sobretitulo">{{ sobretitulo }}</p>
            <h2 :id="idTitulo" class="dialogo__titulo">{{ titulo }}</h2>
          </div>

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

        <div class="dialogo__cuerpo">
          <slot />
        </div>

        <footer v-if="$slots.pie" class="dialogo__pie">
          <slot name="pie" />
        </footer>
      </div>
    </div>
  </Transition>
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
  background: var(--faro-velo);
  cursor: default;
}

.dialogo {
  position: relative;
  display: flex;
  flex-direction: column;
  width: 100%;
  /* La misma columna que el resto de la aplicación: en un teléfono ocupa todo
     el ancho y en una ventana intermedia no se estira más que la pantalla. */
  max-width: var(--faro-ancho-max);
  max-height: 92dvh;
  background: var(--faro-fondo-final);
  border-radius: var(--faro-radio-32) var(--faro-radio-32) 0 0;
  box-shadow: var(--faro-elev-dialogo);
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
  display: flex;
  align-items: flex-start;
  gap: var(--faro-esp-12);
  padding: var(--faro-esp-18) var(--faro-esp-16) var(--faro-esp-14);
  background: var(--faro-superficie);
  border-radius: var(--faro-radio-32) var(--faro-radio-32) 0 0;
  border-bottom: 1px solid var(--faro-linea);
}

/* El asa no se arrastra: dice que esto sube y baja, no que sea una página. */
.dialogo__asa {
  position: absolute;
  top: var(--faro-esp-8);
  left: 50%;
  width: 38px;
  height: 4px;
  background: var(--faro-punto-inactivo);
  border-radius: var(--faro-radio-pastilla);
  transform: translateX(-50%);
}

.dialogo__rotulos {
  flex: 1;
  min-width: 0;
}

.dialogo__sobretitulo {
  font-size: var(--faro-fs-11);
  font-weight: 700;
  letter-spacing: var(--faro-track-012);
  text-transform: uppercase;
  color: var(--faro-gris-texto);
}

.dialogo__titulo {
  margin-top: var(--faro-esp-4);
  font-size: var(--faro-fs-17);
  font-weight: 700;
  color: var(--faro-marca-profundo);
}

.dialogo__cerrar {
  display: grid;
  flex: none;
  place-items: center;
  width: var(--faro-toque);
  height: var(--faro-toque);
  margin: calc(var(--faro-esp-10) * -1) calc(var(--faro-esp-6) * -1) 0 0;
  color: var(--faro-marca-texto);
  border-radius: 50%;
}

.dialogo__cerrar:hover {
  background: var(--faro-fila-activa);
}

.dialogo__cerrar:focus-visible {
  outline: var(--faro-foco-grosor) solid var(--faro-foco-oscuro);
  outline-offset: var(--faro-foco-offset);
}

.dialogo__aspa {
  width: var(--faro-icono-16);
  height: var(--faro-icono-16);
}

.dialogo__cuerpo {
  flex: 1;
  /* Sin esto, un hijo de flex no baja de su alto de contenido y el diálogo
     entero crecería en vez de desplazarse por dentro. */
  min-height: 0;
  padding: var(--faro-esp-16);
  overflow-y: auto;
  /* Al llegar al final, la página de debajo no se lleva el desplazamiento. */
  overscroll-behavior: contain;
}

.dialogo__pie {
  padding: var(--faro-esp-12) var(--faro-esp-16)
    calc(var(--faro-esp-16) + env(safe-area-inset-bottom, 0px));
  background: var(--faro-superficie);
  border-top: 1px solid var(--faro-linea);
}

/*
 * La variante centrada. No es una hoja apoyada en el borde: flota, así que
 * lleva radio por los cuatro lados y un margen que la separa de los bordes de
 * la ventana incluso en un teléfono.
 */
.velo--centrado {
  align-items: center;
  padding: var(--faro-esp-20);
}

.velo--centrado .dialogo {
  max-width: var(--faro-ancho-dialogo);
  max-height: min(88dvh, 720px);
  border-radius: var(--faro-radio-32);
}

.velo--centrado .dialogo__cabecera {
  border-radius: var(--faro-radio-32) var(--faro-radio-32) 0 0;
}

.velo--centrado .dialogo__pie {
  padding-bottom: var(--faro-esp-16);
  border-radius: 0 0 var(--faro-radio-32) var(--faro-radio-32);
}

/*
 * Obligatorio: el velo es más denso que el de un diálogo que se puede cerrar.
 * No es decoración, es la diferencia que se ve sin leer nada —esto no es una
 * capa sobre la pantalla, es lo único que hay— y por eso el contexto de debajo
 * deja de reconocerse, que en cualquier otro diálogo sería un error.
 */
.velo--obligatorio .velo__fondo {
  background: var(--faro-velo-obligatorio);
}

/*
 * El movimiento.
 *
 * La hoja sube y baja; el diálogo centrado crece y se apaga en el sitio. En los
 * dos casos el velo solo cambia de opacidad: mover el velo lo convertiría en
 * una pieza más y es un fondo.
 *
 * La curva no es simétrica a propósito: entra frenando largo, que es lo que
 * hace que parezca que algo pesado se posa, y sale más corta y más recta,
 * porque una salida lenta se lee como que la aplicación va lenta.
 */
.hoja-enter-active,
.centro-enter-active {
  transition: opacity var(--faro-dur-entrada) var(--faro-curva-hoja);
}

.hoja-leave-active,
.centro-leave-active {
  transition: opacity var(--faro-dur-salida) ease-in;
}

.hoja-enter-active .dialogo,
.centro-enter-active .dialogo {
  transition: transform var(--faro-dur-entrada) var(--faro-curva-hoja);
}

.hoja-leave-active .dialogo,
.centro-leave-active .dialogo {
  transition: transform var(--faro-dur-salida) ease-in;
}

.hoja-enter-from,
.hoja-leave-to,
.centro-enter-from,
.centro-leave-to {
  opacity: 0;
}

.hoja-enter-from .dialogo,
.hoja-leave-to .dialogo {
  transform: translateY(100%);
}

.centro-enter-from .dialogo,
.centro-leave-to .dialogo {
  transform: scale(0.94);
}

/*
 * Quien pide menos movimiento no pide menos diálogo: sigue apareciendo y
 * desapareciendo con una opacidad corta, que orienta igual, y lo que se quita
 * es el desplazamiento.
 */
@media (prefers-reduced-motion: reduce) {
  .hoja-enter-active .dialogo,
  .hoja-leave-active .dialogo,
  .centro-enter-active .dialogo,
  .centro-leave-active .dialogo {
    transition: none;
  }

  .hoja-enter-from .dialogo,
  .hoja-leave-to .dialogo,
  .centro-enter-from .dialogo,
  .centro-leave-to .dialogo {
    transform: none;
  }
}

@media (min-width: 900px) {
  .velo {
    align-items: center;
    padding: var(--faro-esp-32);
  }

  .dialogo {
    max-width: var(--faro-ancho-dialogo);
    max-height: min(88dvh, 760px);
    border-radius: var(--faro-radio-32);
  }

  .dialogo__cabecera {
    padding: var(--faro-esp-20) var(--faro-esp-24) var(--faro-esp-16);
    border-radius: var(--faro-radio-32) var(--faro-radio-32) 0 0;
  }

  /* El asa es un gesto de móvil: en escritorio no dice nada. */
  .dialogo__asa {
    display: none;
  }

  .dialogo__cuerpo {
    padding: var(--faro-esp-20) var(--faro-esp-24);
  }

  .dialogo__pie {
    padding: var(--faro-esp-16) var(--faro-esp-24);
    border-radius: 0 0 var(--faro-radio-32) var(--faro-radio-32);
  }

  /* Ya centrada por el punto de corte: lo que sube desde abajo en un teléfono
     aparece en el sitio en escritorio, igual que la variante centrada. */
  .hoja-enter-from .dialogo,
  .hoja-leave-to .dialogo {
    transform: scale(0.96);
  }
}
</style>
