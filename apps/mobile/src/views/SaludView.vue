<script setup lang="ts">
import { FARO_TEXTS_ES } from "@faro/contract/texts";
import { computed, onMounted } from "vue";

import AvisoPendiente from "@/components/salud/AvisoPendiente.vue";
import CabeceraRiesgo from "@/components/salud/CabeceraRiesgo.vue";
import FondoRiesgo from "@/components/salud/FondoRiesgo.vue";
import NavegadorFecha from "@/components/salud/NavegadorFecha.vue";
import TarjetaFactores from "@/components/salud/TarjetaFactores.vue";
import TarjetaFormularios from "@/components/salud/TarjetaFormularios.vue";
import TarjetaRecomendacion from "@/components/salud/TarjetaRecomendacion.vue";
import TarjetaResultado from "@/components/salud/TarjetaResultado.vue";
import { useDiaSeleccionado } from "@/composables/useDiaSeleccionado";
import { useResumenSalud } from "@/composables/useResumenSalud";
import { useNino } from "@/estado/nino";
import { useResultados } from "@/estado/resultados";
import { CLASE_BANDA, bandaRiesgo } from "@/theme/riesgo";

const emitir = defineEmits<{
  verHistorial: [];
  abrirCuestionario: [fecha: string];
}>();

// Único punto de la pantalla donde entran los datos. Los componentes reciben
// `props` ya traducidas y no saben que existe una API.
const { fechaIso, etiqueta, etiquetaAccesible, diaAnterior, diaSiguiente } = useDiaSeleccionado();
const { resumen, cargando, error, recargar } = useResumenSalud(fechaIso);

// El resultado pendiente no depende del día que se esté mirando: es la pregunta
// que el sistema dejó abierta y que hay que contestar antes de que venza.
const { ninoId } = useNino();
const {
  error: errorResultado,
  enviando,
  pendienteDe,
  reportar,
  cargar: cargarResultados,
} = useResultados();

const resultadoPendiente = computed(() => pendienteDe(ninoId.value));

onMounted(cargarResultados);

/** Reportar cambia la estimación del día: el resumen se vuelve a pedir. */
async function alReportar(valor: "yes" | "no"): Promise<void> {
  const solicitud = resultadoPendiente.value;
  if (solicitud === null) return;
  if (await reportar(solicitud, valor)) await recargar();
}

// Mientras se carga o cuando falla no hay estimación, y eso es exactamente la
// banda `desconocido`: gris, no celeste. Pintar de "riesgo bajo" un día del que
// todavía no se sabe nada sería afirmar algo que la API no dijo.
const banda = computed(() => bandaRiesgo(resumen.value?.riesgo ?? null));

function masInfo(): void {
  // TODO(spec): abrir el popup que explica el riesgo de desregulación.
}

// El envío del cuestionario deja viejo el resumen del día: App lo avisa por aquí.
defineExpose({ recargar });
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
            :riesgo="resumen?.riesgo ?? null"
            :confianza="resumen?.confianza ?? null"
            @mas-info="masInfo"
          />
        </div>
      </div>

      <div class="pantalla__contenido">
        <!-- Carga y error ocupan el sitio de las tarjetas, no se superponen a
             ellas: el contenido de un día nunca se lee bajo el de otro. -->
        <p v-if="cargando" class="pantalla__aviso" role="status">
          {{ FARO_TEXTS_ES.loadingEs }}
        </p>

        <p v-else-if="error" class="pantalla__aviso" role="alert">
          {{ error.mensajeEs }}
        </p>

        <template v-else-if="resumen">
          <TarjetaRecomendacion :recomendacion="resumen.recomendacion" />
          <TarjetaFactores :factores="resumen.factores" />
          <!-- "ver más" abre el calendario semanal; cada fila abre el
               cuestionario de su día. El id de la fila es su fecha ISO. -->
          <TarjetaFormularios
            :registros="resumen.formularios"
            @ver-mas="emitir('verHistorial')"
            @abrir-registro="(id) => emitir('abrirCuestionario', id)"
          />
          <TarjetaResultado
            v-if="resultadoPendiente"
            :solicitud="resultadoPendiente"
            :enviando="enviando !== null"
            :error="errorResultado"
            @reportar="alReportar"
          />

          <AvisoPendiente
            v-if="resumen.formularioPendiente"
            :dia="etiquetaAccesible"
            @abrir-formulario="emitir('abrirCuestionario', fechaIso)"
          />
        </template>
      </div>
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
  /* Plano a propósito. Las burbujas son de la columna, que es el lienzo de la
     aplicación; extenderlas a todo el ancho las estiraría hasta desaparecer en
     una ventana de escritorio. */
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
  /* Las burbujas se dimensionan contra esta caja, así que llenan la columna
     igual en un teléfono que en una ventana ancha. */
  background: var(--faro-fondo-pagina);
  border-radius: 50% 50% 0 0 / var(--faro-cupula) var(--faro-cupula) 0 0;
}

/*
 * Carga y error. Una tarjeta más del mismo sistema —misma superficie, mismo
 * radio, misma elevación— y no un bloque aparte: el sitio donde iban a estar
 * las tarjetas no cambia de aspecto según qué haya pasado con la red.
 *
 * `margin-bottom: auto` se come el espacio libre por debajo, así que el aviso
 * queda arriba del todo pese al `space-between` de la columna: justo donde el
 * ojo ya estaba buscando la recomendación.
 */
.pantalla__aviso {
  margin-bottom: auto;
  padding: var(--faro-esp-18) var(--faro-esp-16);
  font-size: var(--faro-fs-135);
  color: var(--faro-gris-texto);
  text-align: center;
  background: var(--faro-superficie);
  border-radius: var(--faro-radio-24);
  box-shadow: var(--faro-sombra-tarjeta);
}
</style>
