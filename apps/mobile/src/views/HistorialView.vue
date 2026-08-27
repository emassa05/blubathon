<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import { BLUBATHON_TEXTS_ES } from "@/api/contrato";
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

        <p v-if="cargando && !cargado" class="historial__estado">
          {{ BLUBATHON_TEXTS_ES.loadingEs }}
        </p>

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
  gap: var(--blubathon-esp-14);
  width: 100%;
  min-height: 100dvh;
  /* El acolchado lateral es el de siempre mientras la ventana no pase del ancho
     de lectura, y a partir de ahí es lo que sobra repartido a los dos lados.
     En un teléfono la resta es negativa y gana el 24 de siempre. */
  padding: calc(var(--blubathon-esp-18) + env(safe-area-inset-top, 0px))
    max(var(--blubathon-esp-24), (100% - var(--blubathon-ancho-lectura)) / 2)
    calc(var(--blubathon-esp-26) + env(safe-area-inset-bottom, 0px));
  /* Las burbujas se dimensionan contra esta caja, igual que en Salud. */
  background: var(--blubathon-fondo-pagina);
}

/*
 * Envuelve. El nombre de quien se sigue es un dato del servidor y puede ser tan
 * largo como se quiera: con `flex: none` y sin envolver, en un teléfono estrecho
 * se comía el ancho y dejaba "Cuestionarios" partido en dos renglones de una
 * palabra cada uno. Ahora la pastilla baja de línea antes de estrujar el título.
 */
.historial__cabecera {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--blubathon-esp-8) var(--blubathon-esp-12);
}

.historial__volver {
  display: grid;
  flex: none;
  place-items: center;
  width: var(--blubathon-toque);
  height: var(--blubathon-toque);
  margin-left: calc(var(--blubathon-esp-10) * -1);
  color: var(--blubathon-marca-accion);
  border-radius: 50%;
}

.historial__volver:hover {
  background: var(--blubathon-fila-activa);
}

.historial__volver:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-foco-oscuro);
  outline-offset: var(--blubathon-foco-offset);
}

.historial__flecha {
  width: var(--blubathon-icono-16);
  height: var(--blubathon-icono-16);
}

.historial__rotulos {
  /* Base 10rem: por debajo de eso el título prefiere llevarse la pastilla a la
     línea siguiente antes que partirse él. */
  flex: 1 1 10rem;
  min-width: 0;
}

.historial__sobretitulo {
  font-size: var(--blubathon-fs-11);
  font-weight: 700;
  letter-spacing: var(--blubathon-track-014);
  text-transform: uppercase;
  color: var(--blubathon-gris-texto);
}

.historial__titulo {
  font-size: var(--blubathon-fs-20);
  font-weight: 700;
  color: var(--blubathon-marca-profundo);
}

.historial__nino {
  flex: 0 1 auto;
  overflow: hidden;
  max-width: 100%;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: var(--blubathon-esp-6) var(--blubathon-esp-12);
  font-size: var(--blubathon-fs-125);
  font-weight: 700;
  color: var(--blubathon-marca-accion);
  background: var(--blubathon-marca-icono-fondo);
  border-radius: var(--blubathon-radio-pastilla);
}

.historial__cuerpo {
  display: flex;
  flex-direction: column;
  gap: var(--blubathon-esp-14);
}

.historial__columna {
  display: flex;
  flex-direction: column;
  gap: var(--blubathon-esp-14);
  min-width: 0;
}

/*
 * El panel del calendario respira menos por los lados que las otras tarjetas: es
 * la única pieza que necesita todo el ancho para que la celda del día siga
 * siendo pulsable en un teléfono estrecho.
 */
.historial__panel {
  padding: var(--blubathon-esp-14) var(--blubathon-esp-6);
  background: var(--blubathon-superficie);
  border-radius: var(--blubathon-radio-24);
  box-shadow: var(--blubathon-elev-1);
}

.historial__calendario {
  margin-top: var(--blubathon-esp-14);
}

.historial__estado {
  padding: var(--blubathon-esp-12) var(--blubathon-esp-14);
  font-size: var(--blubathon-fs-125);
  color: var(--blubathon-gris-texto);
  background: var(--blubathon-superficie);
  border-radius: var(--blubathon-radio-14);
}

.historial__estado--fallo {
  color: var(--blubathon-critica-alta-texto);
  background: var(--blubathon-critica-alta-fondo);
}

.historial__rail {
  min-width: 0;
}

@media (min-width: 900px) {
  .historial {
    /* El 32 sustituye al 24 como suelo del acolchado; el ancho de lectura ya
       vale 1040 y el resto de la cuenta no cambia. */
    padding-inline: max(var(--blubathon-esp-32), (100% - var(--blubathon-ancho-lectura)) / 2);
    gap: var(--blubathon-esp-20);
  }

  .historial__cuerpo {
    display: grid;
    grid-template-columns: minmax(0, 1fr) var(--blubathon-rail-ancho);
    gap: var(--blubathon-esp-20);
    align-items: start;
  }

  .historial__panel {
    padding: var(--blubathon-esp-20) var(--blubathon-esp-16);
  }

  /* El detalle acompaña al calendario mientras se recorre la semana. */
  .historial__rail {
    position: sticky;
    top: var(--blubathon-esp-20);
  }
}
</style>
