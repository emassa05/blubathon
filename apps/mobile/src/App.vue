<script setup lang="ts">
import { ref } from "vue";

import { ES_TERAPEUTA } from "@/api/config";
import DialogoModal from "@/components/base/DialogoModal.vue";
import DialogoCuestionario from "@/components/cuestionario/DialogoCuestionario.vue";
import { useHistorial } from "@/estado/historial";
import { useNino } from "@/estado/nino";
import { useRecomendacionHoy } from "@/estado/recomendacion";
import { useResultados } from "@/estado/resultados";
import HistorialView from "@/views/HistorialView.vue";
import SaludView from "@/views/SaludView.vue";
import TerapeutaView from "@/views/TerapeutaView.vue";

/**
 * Dos perfiles: el del cuidador y el del terapeuta.
 *
 * El del terapeuta es una pantalla sola y se decide en el arranque, con
 * `?rol=terapeuta`: no es un destino al que se navegue desde dentro de la
 * aplicación del cuidador, es otro producto sobre los mismos datos. Por eso
 * sale antes que todo lo demás y no comparte ni la carga del niño ni el
 * diálogo del cuestionario, que son cosas del cuidador.
 *
 * Dentro del perfil del cuidador, dos pantallas y un diálogo, sin router.
 * No hay más navegación que esa —Salud, el historial y el cuestionario que se
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
/**
 * Si el cuestionario que está abierto llegó a enviarse.
 *
 * Es lo que separa cerrar de terminar: se cierra igual con la equis que con el
 * "Listo" de la confirmación, y solo en el segundo caso hay una estimación
 * nueva que enseñar.
 */
const enviado = ref(false);

const { ninoId } = useNino();
const { cargar: cargarHistorial } = useHistorial();
const { cargar: cargarRecomendacion } = useRecomendacionHoy();
const { cargar: cargarResultados } = useResultados();

// Salud trae sus datos por su cuenta, así que se le pide el refresco a ella.
const salud = ref<{
  recargar: () => Promise<void>;
  animarRiesgoDesdeCero: () => void;
  prepararRiesgo: () => void;
} | null>(null);

function abrirCuestionario(fecha: string): void {
  cuestionario.value = fecha;
  enviado.value = false;
}

/**
 * Al cerrar el cuestionario se vuelve a la pantalla que había debajo. Si se
 * envió, la cifra del riesgo se cuenta desde cero: ya está calculada con este
 * día —`alEnviar` recargó el resumen—, pero se calculó con el diálogo delante y
 * nadie la vio moverse.
 *
 * Desde el historial no hay cifra a la vista y `salud` es `null`: no pasa nada,
 * y al volver a Salud la cabecera se monta con su valor puesto.
 */
function cerrarCuestionario(): void {
  cuestionario.value = null;
  if (!enviado.value) return;
  enviado.value = false;
  salud.value?.animarRiesgoDesdeCero();
}

async function alEnviar(): Promise<void> {
  enviado.value = true;
  // Antes de recargar: la cifra se aparca en cero ahora, con el diálogo aún
  // delante, para que el valor nuevo no asome durante la transición de salida y
  // vuelva a caer a cero cuando arranque la cuenta.
  salud.value?.prepararRiesgo();
  if (ninoId.value === null) return;
  await Promise.all([
    cargarHistorial(ninoId.value, true),
    cargarRecomendacion(ninoId.value, true),
    // Cada envío abre un episodio, y con él la solicitud de resultado que
    // habrá que contestar mañana. Sin refrescar, la tarjeta no aparecería
    // hasta recargar la página.
    cargarResultados(true),
    salud.value?.recargar() ?? Promise.resolve(),
  ]);
}
</script>

<template>
  <!-- El perfil del terapeuta no comparte nada con el del cuidador salvo la
       API: ni la fecha seleccionada, ni el niño en curso, ni el cuestionario. -->
  <TerapeutaView v-if="ES_TERAPEUTA" />

  <template v-else>
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
    @cerrar="cerrarCuestionario"
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
        El cuestionario se envía a la API de Blubathon y ahora mismo no responde. Comprueba que esté
        levantada en <code>http://127.0.0.1:8000</code> y vuelve a intentarlo.
      </p>
    </DialogoModal>
  </template>
</template>

<style scoped>
.sin-api {
  padding: var(--blubathon-esp-14);
  font-size: var(--blubathon-fs-135);
  line-height: 1.5;
  color: var(--blubathon-marca-texto);
  background: var(--blubathon-superficie);
  border-radius: var(--blubathon-radio-14);
}

.sin-api code {
  font-size: var(--blubathon-fs-125);
  color: var(--blubathon-marca-profundo);
}
</style>
