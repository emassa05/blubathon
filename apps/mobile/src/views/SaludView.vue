<script setup lang="ts">
import AvisoPendiente from "@/components/salud/AvisoPendiente.vue";
import CabeceraBienestar from "@/components/salud/CabeceraBienestar.vue";
import NavegadorFecha from "@/components/salud/NavegadorFecha.vue";
import TarjetaFactores from "@/components/salud/TarjetaFactores.vue";
import TarjetaFormularios from "@/components/salud/TarjetaFormularios.vue";
import TarjetaRecomendacion from "@/components/salud/TarjetaRecomendacion.vue";
import { useDiaSeleccionado } from "@/composables/useDiaSeleccionado";
import { RESUMEN_SALUD_MOCK } from "@/data/saludMock";

// Único punto de la pantalla donde entran los datos. Cambiar el mock por la
// llamada a la API (o por un store) no toca ningún componente.
const resumen = RESUMEN_SALUD_MOCK;

const { etiqueta, etiquetaAccesible, diaAnterior, diaSiguiente } = useDiaSeleccionado(
  resumen.fecha,
);

function abrirFormulario(): void {
  // TODO(spec): abrir el formulario del día. Fuera del alcance de esta pantalla.
}

function verMas(): void {
  // TODO(spec): abrir el listado completo de formularios.
}
</script>

<template>
  <main class="pantalla">
    <div class="pantalla__columna">
      <NavegadorFecha
        :etiqueta="etiqueta"
        @dia-anterior="diaAnterior"
        @dia-siguiente="diaSiguiente"
      />

      <CabeceraBienestar class="pantalla__bienestar" :porcentaje="resumen.bienestar" />

      <div class="pantalla__contenido">
        <TarjetaRecomendacion :recomendacion="resumen.recomendacion" />
        <TarjetaFactores :factores="resumen.factores" />
        <TarjetaFormularios :registros="resumen.formularios" @ver-mas="verMas" />
        <AvisoPendiente
          v-if="resumen.formularioPendiente"
          :dia="etiquetaAccesible"
          @abrir-formulario="abrirFormulario"
        />
      </div>
    </div>
  </main>
</template>

<style scoped>
/*
 * El gradiente del diseño está pensado sobre un alto de 844px: si se estira a
 * la ventana entera, en una pantalla alta la banda clara sube y el texto blanco
 * de la cabecera pierde contraste. Por eso se pinta a esa altura, anclado
 * arriba, sobre el color de su última parada: lo que queda por debajo es
 * exactamente el color con el que el gradiente termina, así que no se ve
 * ninguna costura.
 */
.pantalla {
  display: flex;
  /* Sin estirar: en una ventana muy alta la columna se queda en su alto de
     referencia y no reparte los bloques por toda la pantalla. */
  align-items: flex-start;
  justify-content: center;
  min-height: 100dvh;
  background-color: var(--faro-fondo-final);
  background-image: var(--faro-fondo);
  background-repeat: no-repeat;
  background-size: 100% var(--faro-alto-referencia);
}

/*
 * La columna de contenido. Los paddings son fijos y el ancho es flexible, así
 * que la página se comporta igual de 320px a pantalla completa: por debajo del
 * máximo ocupa todo el ancho, por encima se centra.
 *
 * El alto de referencia es el del diseño (844px): en una ventana más alta la
 * columna no se estira sin fin, se queda en esa proporción y se centra; en una
 * más baja, la página se desplaza como cualquier otra.
 */
.pantalla__columna {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: var(--faro-ancho-max);
  min-height: min(100dvh, var(--faro-alto-referencia));
  padding: calc(var(--faro-esp-26) + env(safe-area-inset-top, 0px)) var(--faro-esp-24)
    calc(var(--faro-esp-26) + env(safe-area-inset-bottom, 0px));
}

.pantalla__bienestar {
  margin-top: var(--faro-esp-10);
}

.pantalla__contenido {
  display: flex;
  flex: 1;
  flex-direction: column;
  justify-content: space-between;
  /* `gap` es el mínimo entre bloques; con espacio libre, `space-between` sigue
     repartiéndolo igual. */
  gap: var(--faro-esp-24);
  margin-top: var(--faro-esp-24);
}
</style>
