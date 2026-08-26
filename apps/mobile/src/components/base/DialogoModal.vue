<script setup lang="ts">
import { ref, useId } from "vue";

import IconoCerrar from "@/components/icons/IconoCerrar.vue";
import { useDialogo } from "@/composables/useDialogo";

withDefaults(
  defineProps<{
    titulo: string;
    /** Línea corta encima del título: de qué es este diálogo. */
    sobretitulo?: string;
    etiquetaCerrar?: string;
  }>(),
  { sobretitulo: "", etiquetaCerrar: "Cerrar" },
);

const emitir = defineEmits<{ cerrar: [] }>();

const contenedor = ref<HTMLElement | null>(null);
const idTitulo = useId();

useDialogo(contenedor, () => emitir("cerrar"));
</script>

<template>
  <!--
    Sin `Teleport`: no hay ningún ancestro con `transform`, `filter` ni
    `contain` que rompa un `position: fixed`, así que el diálogo funciona donde
    se declara y las pruebas pueden montarlo sin buscarlo por `document.body`.
  -->
  <div class="velo">
    <!--
      El velo también cierra al pulsarlo, y para eso es un botón de verdad: con
      nombre accesible y fuera del orden de tabulación, porque el control que se
      recorre con el teclado es la aspa de la cabecera, y `Esc` hace lo mismo.
    -->
    <button
      type="button"
      class="velo__fondo"
      tabindex="-1"
      :aria-label="etiquetaCerrar"
      @click="emitir('cerrar')"
    ></button>

    <div
      ref="contenedor"
      class="dialogo"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="idTitulo"
      tabindex="-1"
    >
      <header class="dialogo__cabecera">
        <span class="dialogo__asa" aria-hidden="true"></span>

        <div class="dialogo__rotulos">
          <p v-if="sobretitulo" class="dialogo__sobretitulo">{{ sobretitulo }}</p>
          <h2 :id="idTitulo" class="dialogo__titulo">{{ titulo }}</h2>
        </div>

        <button
          type="button"
          class="dialogo__cerrar"
          :aria-label="etiquetaCerrar"
          @click="emitir('cerrar')"
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
}
</style>
