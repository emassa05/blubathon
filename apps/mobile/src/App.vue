<script setup lang="ts">
import { ref } from "vue";

import DialogoModal from "@/components/base/DialogoModal.vue";
import DialogoCuestionario from "@/components/cuestionario/DialogoCuestionario.vue";
import { useHistorial } from "@/estado/historial";
import { useNino } from "@/estado/nino";
import { useRecomendacionHoy } from "@/estado/recomendacion";
import HistorialView from "@/views/HistorialView.vue";
import SaludView from "@/views/SaludView.vue";

/**
 * Dos pantallas y un diálogo, sin router.
 *
 * No hay más navegación que esta —Salud, el historial y el cuestionario que se
 * abre encima de cualquiera de las dos—, y meter un router para dos destinos
 * sería añadir una dependencia y un modo de fallo por un `v-if`.
 *
 * El diálogo vive aquí, y no dentro de cada pantalla, porque las dos lo abren:
 * así hay un solo cuestionario montado, y al enviarlo se refrescan de una vez
 * las dos llamadas que ese envío deja viejas.
 */
type Vista = "salud" | "historial";

const vista = ref<Vista>("salud");
/** Fecha ISO del cuestionario abierto, o `null` si no hay ninguno. */
const cuestionario = ref<string | null>(null);

const { ninoId } = useNino();
const { cargar: cargarHistorial } = useHistorial();
const { cargar: cargarRecomendacion } = useRecomendacionHoy();

// Salud trae sus datos por su cuenta, así que se le pide el refresco a ella.
const salud = ref<{ recargar: () => Promise<void> } | null>(null);

function abrirCuestionario(fecha: string): void {
  cuestionario.value = fecha;
}

async function alEnviar(): Promise<void> {
  if (ninoId.value === null) return;
  await Promise.all([
    cargarHistorial(ninoId.value, true),
    cargarRecomendacion(ninoId.value, true),
    salud.value?.recargar() ?? Promise.resolve(),
  ]);
}
</script>

<template>
  <SaludView
    v-if="vista === 'salud'"
    ref="salud"
    @ver-historial="vista = 'historial'"
    @abrir-cuestionario="abrirCuestionario"
  />
  <HistorialView v-else @volver="vista = 'salud'" @abrir-cuestionario="abrirCuestionario" />

  <!-- La clave es la fecha: cambiar de día vuelve a montar el diálogo, y con él
       el plan y el borrador. Un cuestionario no se arrastra de un día a otro. -->
  <DialogoCuestionario
    v-if="cuestionario !== null && ninoId !== null"
    :key="cuestionario"
    :nino-id="ninoId"
    :fecha="cuestionario"
    @cerrar="cuestionario = null"
    @enviado="alEnviar"
  />

  <!-- Sin la lista de `GET /children` no hay `child_id`, y sin `child_id` no
       hay ninguna llamada que hacer. Se dice, en vez de dejar un botón muerto. -->
  <DialogoModal
    v-else-if="cuestionario !== null"
    sobretitulo="Cuestionario diario"
    titulo="No se puede abrir todavía"
    @cerrar="cuestionario = null"
  >
    <p class="sin-api">
      El cuestionario se envía a la API de Faro y ahora mismo no responde. Comprueba que esté
      levantada en <code>http://127.0.0.1:8000</code> y vuelve a intentarlo.
    </p>
  </DialogoModal>
</template>

<style scoped>
.sin-api {
  padding: var(--faro-esp-14);
  font-size: var(--faro-fs-135);
  line-height: 1.5;
  color: var(--faro-verde-texto);
  background: var(--faro-superficie);
  border-radius: var(--faro-radio-14);
}

.sin-api code {
  font-size: var(--faro-fs-125);
  color: var(--faro-verde-profundo);
}
</style>
