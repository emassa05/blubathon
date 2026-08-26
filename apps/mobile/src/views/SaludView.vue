<script setup lang="ts">
import { computed, ref } from "vue";

import AvisoPendiente from "@/components/salud/AvisoPendiente.vue";
import CabeceraRiesgo from "@/components/salud/CabeceraRiesgo.vue";
import FondoRiesgo from "@/components/salud/FondoRiesgo.vue";
import NavegadorFecha from "@/components/salud/NavegadorFecha.vue";
import TarjetaFactores from "@/components/salud/TarjetaFactores.vue";
import TarjetaFormularios from "@/components/salud/TarjetaFormularios.vue";
import TarjetaRecomendacion from "@/components/salud/TarjetaRecomendacion.vue";
import { useDiaSeleccionado } from "@/composables/useDiaSeleccionado";
import { RESUMEN_SALUD_MOCK } from "@/data/saludMock";
import {
  CLASE_BANDA,
  ETIQUETA_BANDA,
  RIESGO_DE_PRUEBA,
  bandaRiesgo,
  bandaSiguiente,
} from "@/theme/riesgo";

// Único punto de la pantalla donde entran los datos. Cambiar el mock por la
// llamada a la API (o por un store) no toca ningún componente.
const resumen = RESUMEN_SALUD_MOCK;

const { etiqueta, etiquetaAccesible, diaAnterior, diaSiguiente } = useDiaSeleccionado(
  resumen.fecha,
);

// TODO(spec): control de prueba. Mientras no haya datos reales, permite ver las
// tres bandas sin tocar el mock. Se va junto con `RIESGO_DE_PRUEBA`.
const riesgoDePrueba = ref<number | null>(null);

const riesgo = computed(() => riesgoDePrueba.value ?? resumen.riesgo);
const banda = computed(() => bandaRiesgo(riesgo.value));

function probarBandaSiguiente(): void {
  riesgoDePrueba.value = RIESGO_DE_PRUEBA[bandaSiguiente(banda.value)];
}

function masInfo(): void {
  // TODO(spec): abrir el popup que explica el riesgo de desregulación.
}

function abrirFormulario(): void {
  // TODO(spec): abrir el formulario del día. Fuera del alcance de esta pantalla.
}

function verMas(): void {
  // TODO(spec): abrir el listado completo de formularios.
}

function abrirRegistro(_id: string): void {
  // TODO(spec): abrir el formulario de ese día. El id es el que trae el mock.
}
</script>

<template>
  <main class="pantalla">
    <!-- La banda es lo único que decide el color: la clase lleva la paleta
         entera y de aquí la heredan el panel y la tarjeta de recomendación. -->
    <div class="pantalla__columna" :class="CLASE_BANDA[banda]">
      <div class="pantalla__panel">
        <FondoRiesgo :banda="banda" />

        <div class="pantalla__panel-contenido">
          <NavegadorFecha
            :etiqueta="etiqueta"
            @dia-anterior="diaAnterior"
            @dia-siguiente="diaSiguiente"
          />

          <CabeceraRiesgo
            class="pantalla__riesgo"
            :riesgo="riesgo"
            :confianza="resumen.confianza"
            @mas-info="masInfo"
          />
        </div>
      </div>

      <div class="pantalla__contenido">
        <TarjetaRecomendacion :recomendacion="resumen.recomendacion" />
        <TarjetaFactores :factores="resumen.factores" />
        <TarjetaFormularios
          :registros="resumen.formularios"
          @ver-mas="verMas"
          @abrir-registro="abrirRegistro"
        />
        <AvisoPendiente
          v-if="resumen.formularioPendiente"
          :dia="etiquetaAccesible"
          @abrir-formulario="abrirFormulario"
        />
      </div>

      <!-- TODO(spec): temporal, para revisar el diseño de las tres bandas. -->
      <button
        type="button"
        class="pantalla__prueba"
        :aria-label="`Prueba: cambiar a riesgo ${ETIQUETA_BANDA[bandaSiguiente(banda)].toLowerCase()}`"
        :title="`Prueba: riesgo ${ETIQUETA_BANDA[banda].toLowerCase()}`"
        @click="probarBandaSiguiente"
      >
        <span class="pantalla__prueba-punto" aria-hidden="true"></span>
      </button>
    </div>
  </main>
</template>

<style scoped>
.pantalla {
  display: flex;
  /* Sin estirar: en una ventana muy alta la columna se queda en su alto de
     referencia y no reparte los bloques por toda la pantalla. */
  align-items: flex-start;
  justify-content: center;
  min-height: 100dvh;
  background: var(--faro-fondo-final);
}

/*
 * La columna de contenido. El ancho es flexible, así que la página se comporta
 * igual de 320px a pantalla completa: por debajo del máximo ocupa todo el
 * ancho, por encima se centra.
 *
 * No lleva padding lateral: el panel va a sangre y el acolchado de 24 lo ponen
 * el propio panel y el bloque de tarjetas.
 */
.pantalla__columna {
  position: relative;
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: var(--faro-ancho-max);
  min-height: min(100dvh, var(--faro-alto-referencia));
  padding-bottom: calc(var(--faro-esp-26) + env(safe-area-inset-bottom, 0px));
}

/*
 * El panel del riesgo: un gradiente de la banda, casi blanco arriba y con
 * color abajo, más un brillo difuso muy abierto en la parte de arriba. El texto
 * cae siempre en la zona clara, que es donde más contraste hay, y el color se
 * concentra donde se ve la cúpula.
 *
 * Abajo no lleva radio: la curva la recorta el contenido, que sube sobre él.
 *
 * `min-height` es un mínimo, no un alto: si el texto crece con el zoom, el
 * panel crece con él. La barra de estado del dispositivo se suma al acolchado
 * de arriba.
 */
.pantalla__panel {
  position: relative;
  display: flex;
  flex-direction: column;
  min-height: var(--faro-panel-alto);
  padding: calc(var(--faro-esp-14) + env(safe-area-inset-top, 0px)) var(--faro-esp-24)
    var(--faro-esp-26);
  overflow: hidden;
  background:
    radial-gradient(130% 62% at 50% 0%, var(--faro-brillo), transparent 62%),
    linear-gradient(180deg, var(--faro-panel-cima) 0%, var(--faro-panel) 100%);
}

.pantalla__panel-contenido {
  position: relative;
}

.pantalla__riesgo {
  margin-top: var(--faro-esp-4);
}

/*
 * El contenido no empieza donde acaba el panel: sube sobre él y lo recorta con
 * una cúpula, de modo que el panel llega más abajo por los lados que por el
 * centro. Es el mismo color de la página, así que lo único que se ve es el
 * corte.
 *
 * La curva son los dos radios de arriba con el eje horizontal al 50%: las dos
 * elipses se encuentran justo en el centro y forman un arco continuo, sin la
 * esquina que deja un `border-radius` normal.
 *
 * El acolchado de arriba devuelve exactamente lo que se comió el margen
 * negativo, así que la cúpula no le cuesta ni un píxel de alto a la página.
 */
.pantalla__contenido {
  position: relative;
  display: flex;
  flex: 1;
  flex-direction: column;
  justify-content: space-between;
  /* `gap` es el mínimo entre bloques; con espacio libre, `space-between` sigue
     repartiéndolo igual. */
  gap: var(--faro-esp-14);
  padding: calc(var(--faro-esp-14) + var(--faro-cupula)) var(--faro-esp-24) 0;
  margin-top: calc(var(--faro-cupula) * -1);
  background: var(--faro-fondo-final);
  border-radius: 50% 50% 0 0 / var(--faro-cupula) var(--faro-cupula) 0 0;
}

/*
 * Control de prueba. Flota en una esquina y fuera del flujo: no le cuesta ni un
 * píxel de alto a la composición, y al quitarlo la pantalla queda exactamente
 * igual. Redondo y sin rótulo porque el estado ya lo dice el color de toda la
 * pantalla; el nombre accesible sí dice a qué banda cambia.
 */
.pantalla__prueba {
  position: fixed;
  bottom: calc(var(--faro-esp-12) + env(safe-area-inset-bottom, 0px));
  left: var(--faro-esp-12);
  z-index: 1;
  display: grid;
  place-items: center;
  width: var(--faro-toque);
  height: var(--faro-toque);
  background: var(--faro-superficie);
  border-radius: 50%;
  box-shadow: var(--faro-sombra-tarjeta);
}

.pantalla__prueba:focus-visible {
  outline: var(--faro-foco-grosor) solid var(--faro-foco-oscuro);
  outline-offset: var(--faro-foco-offset);
}

.pantalla__prueba-punto {
  width: var(--faro-icono-14);
  height: var(--faro-icono-14);
  background: var(--faro-panel);
  border: 1px solid var(--faro-onda-3);
  border-radius: 50%;
}
</style>
