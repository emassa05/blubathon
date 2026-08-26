<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import { FARO_TEXTS_ES } from "@/api/contrato";
import CalendarioSemanal from "@/components/historial/CalendarioSemanal.vue";
import DetalleDia from "@/components/historial/DetalleDia.vue";
import NavegadorSemana from "@/components/historial/NavegadorSemana.vue";
import ResumenSemana from "@/components/historial/ResumenSemana.vue";
import IconoFlecha from "@/components/icons/IconoFlecha.vue";
import { resumenDeDia, type CeldaCalendario } from "@/dominio/dia";
import { desplazarSemana, hoyIso, lunesDe, semanaDe } from "@/dominio/semana";
import { useHistorial } from "@/estado/historial";
import { useNino } from "@/estado/nino";
import { diasConRespuestas, respuestasDe } from "@/estado/respuestas";

const emitir = defineEmits<{
  volver: [];
  abrirCuestionario: [fecha: string];
}>();

const { ninoId, etiqueta: nombreDelNino, cargar: cargarNino } = useNino();
const { porFecha, cargando, cargado, error, cargar: cargarHistorial } = useHistorial();

const hoy = ref(hoyIso());
const inicioSemana = ref(lunesDe(hoy.value));
const seleccionado = ref(hoy.value);

const semana = computed(() => semanaDe(inicioSemana.value, hoy.value));

/** Los días ya guardados de esa persona, base de la comparación con lo habitual. */
const anteriores = computed(() => (ninoId.value === null ? [] : diasConRespuestas(ninoId.value)));

const celdas = computed<readonly CeldaCalendario[]>(() =>
  semana.value.dias.map((dia) => ({
    dia,
    resumen: resumenDeDia(
      dia.iso,
      hoy.value,
      porFecha.value.get(dia.iso),
      ninoId.value === null ? undefined : respuestasDe(ninoId.value, dia.iso),
      anteriores.value.filter((anterior) => anterior.fecha !== dia.iso),
    ),
  })),
);

const detalle = computed(
  () =>
    celdas.value.find((celda) => celda.dia.iso === seleccionado.value)?.resumen ??
    celdas.value[0]?.resumen,
);

onMounted(async () => {
  await cargarNino();
  if (ninoId.value !== null) await cargarHistorial(ninoId.value);
});

/** Al cambiar de semana, se abre el último día que ya pasó: el más informativo. */
watch(inicioSemana, () => {
  const dentro = semana.value.dias.some((dia) => dia.iso === seleccionado.value);
  if (dentro) return;
  const pasados = semana.value.dias.filter((dia) => !dia.esFuturo);
  seleccionado.value = pasados[pasados.length - 1]?.iso ?? semana.value.inicio;
});

function irASemana(cantidad: number): void {
  inicioSemana.value = desplazarSemana(inicioSemana.value, cantidad);
}
</script>

<template>
  <main class="historial">
    <header class="historial__cabecera">
      <button
        type="button"
        class="historial__volver"
        aria-label="Volver a Salud"
        @click="emitir('volver')"
      >
        <IconoFlecha class="historial__flecha" />
      </button>

      <div class="historial__rotulos">
        <p class="historial__sobretitulo">Historial</p>
        <h1 class="historial__titulo">Cuestionarios</h1>
      </div>

      <p v-if="nombreDelNino" class="historial__nino">{{ nombreDelNino }}</p>
    </header>

    <div class="historial__cuerpo">
      <div class="historial__columna">
        <section class="historial__panel">
          <NavegadorSemana
            :semana="semana"
            @semana-anterior="irASemana(-1)"
            @semana-siguiente="irASemana(1)"
          />

          <CalendarioSemanal
            class="historial__calendario"
            :celdas="celdas"
            :seleccionado="seleccionado"
            @seleccionar="(iso) => (seleccionado = iso)"
          />
        </section>

        <ResumenSemana :celdas="celdas" />

        <p v-if="cargando && !cargado" class="historial__estado">{{ FARO_TEXTS_ES.loadingEs }}</p>

        <!-- Sin API el calendario sigue en pie: lo que se ve son los envíos que
             guardó este dispositivo, y eso se dice, no se disimula. -->
        <p v-else-if="error" class="historial__estado historial__estado--fallo">{{ error }}</p>
      </div>

      <div class="historial__rail">
        <DetalleDia
          v-if="detalle"
          :resumen="detalle"
          @abrir-cuestionario="emitir('abrirCuestionario', detalle.fecha)"
        />
      </div>
    </div>
  </main>
</template>

<style scoped>
/*
 * La misma columna de 480 que la pantalla de Salud mientras haya un solo brazo.
 * A partir de 900 el calendario y el detalle dejan de turnarse en vertical y se
 * ponen uno al lado del otro: en escritorio, elegir un día y leerlo son el mismo
 * gesto, y desplazarse entre las dos cosas es la única parte que sobraba.
 */
.historial {
  display: flex;
  flex-direction: column;
  gap: var(--faro-esp-14);
  width: 100%;
  max-width: var(--faro-ancho-max);
  min-height: 100dvh;
  padding: calc(var(--faro-esp-18) + env(safe-area-inset-top, 0px)) var(--faro-esp-24)
    calc(var(--faro-esp-26) + env(safe-area-inset-bottom, 0px));
  margin-inline: auto;
  background: var(--faro-fondo-final);
}

.historial__cabecera {
  display: flex;
  align-items: center;
  gap: var(--faro-esp-12);
}

.historial__volver {
  display: grid;
  flex: none;
  place-items: center;
  width: var(--faro-toque);
  height: var(--faro-toque);
  margin-left: calc(var(--faro-esp-10) * -1);
  color: var(--faro-verde-accion);
  border-radius: 50%;
}

.historial__volver:hover {
  background: var(--faro-fila-activa);
}

.historial__volver:focus-visible {
  outline: var(--faro-foco-grosor) solid var(--faro-foco-oscuro);
  outline-offset: var(--faro-foco-offset);
}

.historial__flecha {
  width: var(--faro-icono-16);
  height: var(--faro-icono-16);
}

.historial__rotulos {
  flex: 1;
  min-width: 0;
}

.historial__sobretitulo {
  font-size: var(--faro-fs-11);
  font-weight: 700;
  letter-spacing: var(--faro-track-014);
  text-transform: uppercase;
  color: var(--faro-gris-texto);
}

.historial__titulo {
  font-size: var(--faro-fs-20);
  font-weight: 700;
  color: var(--faro-verde-profundo);
}

.historial__nino {
  flex: none;
  padding: var(--faro-esp-6) var(--faro-esp-12);
  font-size: var(--faro-fs-125);
  font-weight: 700;
  color: var(--faro-verde-accion);
  background: var(--faro-verde-icono-fondo);
  border-radius: var(--faro-radio-pastilla);
}

.historial__cuerpo {
  display: flex;
  flex-direction: column;
  gap: var(--faro-esp-14);
}

.historial__columna {
  display: flex;
  flex-direction: column;
  gap: var(--faro-esp-14);
  min-width: 0;
}

/*
 * El panel del calendario respira menos por los lados que las otras tarjetas: es
 * la única pieza que necesita todo el ancho para que la celda del día siga
 * siendo pulsable en un teléfono estrecho.
 */
.historial__panel {
  padding: var(--faro-esp-14) var(--faro-esp-6);
  background: var(--faro-superficie);
  border-radius: var(--faro-radio-24);
  box-shadow: var(--faro-elev-1);
}

.historial__calendario {
  margin-top: var(--faro-esp-14);
}

.historial__estado {
  padding: var(--faro-esp-12) var(--faro-esp-14);
  font-size: var(--faro-fs-125);
  color: var(--faro-gris-texto);
  background: var(--faro-superficie);
  border-radius: var(--faro-radio-14);
}

.historial__estado--fallo {
  color: var(--faro-critica-alta-texto);
  background: var(--faro-critica-alta-fondo);
}

.historial__rail {
  min-width: 0;
}

@media (min-width: 900px) {
  .historial {
    max-width: var(--faro-ancho-amplio);
    padding-inline: var(--faro-esp-32);
    gap: var(--faro-esp-20);
  }

  .historial__cuerpo {
    display: grid;
    grid-template-columns: minmax(0, 1fr) var(--faro-rail-ancho);
    gap: var(--faro-esp-20);
    align-items: start;
  }

  .historial__panel {
    padding: var(--faro-esp-20) var(--faro-esp-16);
  }

  /* El detalle acompaña al calendario mientras se recorre la semana. */
  .historial__rail {
    position: sticky;
    top: var(--faro-esp-20);
  }
}
</style>
