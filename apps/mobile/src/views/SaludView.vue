<script setup lang="ts">
import AvisoPendiente from "@/components/salud/AvisoPendiente.vue";
import BarraEstado from "@/components/salud/BarraEstado.vue";
import CabeceraBienestar from "@/components/salud/CabeceraBienestar.vue";
import NavegadorFecha from "@/components/salud/NavegadorFecha.vue";
import TarjetaFactores from "@/components/salud/TarjetaFactores.vue";
import TarjetaFormularios from "@/components/salud/TarjetaFormularios.vue";
import TarjetaRecomendacion from "@/components/salud/TarjetaRecomendacion.vue";
import { useDiaSeleccionado } from "@/composables/useDiaSeleccionado";
import { useEstadoDispositivo } from "@/composables/useEstadoDispositivo";
import { RESUMEN_SALUD_MOCK } from "@/data/saludMock";

// Único punto de la pantalla donde entran los datos. Cambiar el mock por la
// llamada a la API (o por un store) no toca ningún componente.
const resumen = RESUMEN_SALUD_MOCK;

const { etiqueta, etiquetaAccesible, diaAnterior, diaSiguiente } = useDiaSeleccionado(
  resumen.fecha,
);
const { hora, bateria } = useEstadoDispositivo();

function abrirFormulario(): void {
  // TODO(spec): abrir el formulario del día. Fuera del alcance de esta pantalla.
}

function verMas(): void {
  // TODO(spec): abrir el listado completo de formularios.
}
</script>

<template>
  <div class="pantalla faro-marco">
    <BarraEstado class="pantalla__barra" :hora="hora" :bateria="bateria" />

    <NavegadorFecha
      class="pantalla__fecha"
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
</template>

<style scoped>
.pantalla {
  position: relative;
  width: 100%;
  min-height: 100dvh;
  overflow: hidden;
  background: var(--faro-fondo);
}

.pantalla__fecha,
.pantalla__bienestar,
.pantalla__contenido {
  position: absolute;
  right: 0;
  left: 0;
}

.pantalla__fecha {
  top: var(--faro-fecha-top);
}

.pantalla__bienestar {
  top: var(--faro-bienestar-top);
}

.pantalla__contenido {
  top: var(--faro-contenido-top);
  bottom: var(--faro-contenido-bottom);
  right: var(--faro-esp-24);
  left: var(--faro-esp-24);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  /* `gap` es un mínimo, no un reparto: con espacio libre, `space-between` sigue
     distribuyéndolo igual. Con zoom al 200% evita que los bloques se toquen. */
  gap: var(--faro-esp-12);
  /* Antes de recortar contenido, que desplace. */
  overflow-y: auto;
  overscroll-behavior: contain;
}

/* Vista de catálogo/preview. El punto de corte (480px) está documentado en
   `styles/tokens.css`: `@media` no acepta `var()`. En un móvil real no aplica y
   la pantalla ocupa el viewport entero, sin esquinas redondeadas. */
@media (min-width: 480px) {
  .pantalla {
    width: var(--faro-marco-ancho);
    height: var(--faro-marco-alto);
    min-height: 0;
    border-radius: var(--faro-radio-44);
    box-shadow: var(--faro-sombra-marco);
  }
}
</style>
