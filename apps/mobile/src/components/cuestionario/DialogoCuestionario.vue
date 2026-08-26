<script setup lang="ts">
import { computed, onMounted } from "vue";

import type { FieldCode, FormSubmissionResponse } from "@/api/contrato";
import { FARO_TEXTS_ES } from "@/api/contrato";
import DialogoModal from "@/components/base/DialogoModal.vue";
import CampoCuestionario from "@/components/cuestionario/CampoCuestionario.vue";
import ListaCriticas from "@/components/cuestionario/ListaCriticas.vue";
import IconoCheck from "@/components/icons/IconoCheck.vue";
import { useCuestionario } from "@/composables/useCuestionario";
import { etiquetaDiaLargo } from "@/dominio/semana";
import { diasConRespuestas, guardarRespuestas, respuestasDe } from "@/estado/respuestas";

const props = defineProps<{
  ninoId: string;
  /** Día del cuestionario, en ISO local. Es el `local_date` del envío. */
  fecha: string;
}>();

const emitir = defineEmits<{
  cerrar: [];
  enviado: [respuesta: FormSubmissionResponse];
}>();

const previas = respuestasDe(props.ninoId, props.fecha);

const cuestionario = useCuestionario({
  ninoId: props.ninoId,
  fecha: props.fecha,
  ...(previas === undefined ? {} : { previas }),
  anteriores: diasConRespuestas(props.ninoId).filter((dia) => dia.fecha !== props.fecha),
});

const {
  cargando,
  error,
  enviando,
  errorEnvio,
  resultado,
  borradores,
  destacadas,
  resto,
  sugerencias,
  contestadas,
  criticas,
  respondidas,
  yaEnviado,
} = cuestionario;

onMounted(() => {
  void cuestionario.cargarPlan();
});

const titulo = computed(() => etiquetaDiaLargo(props.fecha));

/** Qué produjo el envío, dicho en una frase. */
const MENSAJE_ENVIO: Record<FormSubmissionResponse["status"], string> = {
  episode_created: "Registrado. Con este día se abrió una nueva estimación.",
  episode_linked: "Registrado. Se sumó a la estimación que ya estaba abierta.",
  target_definition_unavailable:
    "Registrado. Todavía no hay una definición de resultado vigente, así que este día no abre estimación.",
};

const criticaPorCampo = computed(() => {
  const indice = new Map<FieldCode, (typeof criticas.value)[number]>();
  for (const critica of criticas.value) indice.set(critica.campo, critica);
  return indice;
});

async function enviar(): Promise<void> {
  const respuesta = await cuestionario.enviar();
  if (respuesta === null) return;
  // La copia local se escribe solo cuando la API ya aceptó el envío.
  guardarRespuestas(props.ninoId, props.fecha, { ...respondidas.value });
  emitir("enviado", respuesta);
}
</script>

<template>
  <DialogoModal
    sobretitulo="Cuestionario diario"
    :titulo="titulo"
    etiqueta-cerrar="Cerrar el cuestionario"
    @cerrar="emitir('cerrar')"
  >
    <!-- Enviado: la confirmación ocupa el diálogo entero. -->
    <div v-if="resultado" class="hecho">
      <span class="hecho__insignia" aria-hidden="true">
        <IconoCheck class="hecho__tilde" />
      </span>
      <h3 class="hecho__titulo">Cuestionario guardado</h3>
      <p class="hecho__detalle">{{ MENSAJE_ENVIO[resultado.status] }}</p>

      <ListaCriticas v-if="criticas.length > 0" class="hecho__criticas" :criticas="criticas" />
    </div>

    <template v-else>
      <p v-if="cargando" class="estado">{{ FARO_TEXTS_ES.loadingEs }}</p>

      <!-- El plan es una ayuda, no un requisito: sin él se pregunta el catálogo
           entero en orden canónico y el cuestionario se puede enviar igual. -->
      <p v-if="error" class="estado estado--fallo">
        {{ error }} Se preguntan todos los campos, en su orden.
      </p>

      <p v-if="yaEnviado" class="estado estado--aviso">
        Este día ya tiene un cuestionario enviado. Al guardar se registra una respuesta nueva, no se
        reemplaza la anterior.
      </p>

      <ListaCriticas v-if="criticas.length > 0" class="bloque" :criticas="criticas" />

      <section v-if="destacadas.length > 0" class="bloque grupo">
        <h3 class="grupo__titulo">Lo primero de hoy</h3>
        <p class="grupo__subtitulo">
          El formulario elige estas preguntas por lo que falta o por lo que hace días que no se
          registra.
        </p>

        <CampoCuestionario
          v-for="pregunta in destacadas"
          :key="pregunta.field_code"
          :pregunta="pregunta"
          :borrador="borradores[pregunta.field_code]"
          :sugerencia="sugerencias.get(pregunta.field_code)"
          :critica="criticaPorCampo.get(pregunta.field_code)"
          @responder="
            (valor, interaccion) => cuestionario.responder(pregunta.field_code, valor, interaccion)
          "
          @no-sabe="cuestionario.noSabe(pregunta.field_code)"
        />
      </section>

      <section class="bloque grupo">
        <h3 class="grupo__titulo">El resto del día</h3>

        <CampoCuestionario
          v-for="pregunta in resto"
          :key="pregunta.field_code"
          :pregunta="pregunta"
          :borrador="borradores[pregunta.field_code]"
          :sugerencia="sugerencias.get(pregunta.field_code)"
          :critica="criticaPorCampo.get(pregunta.field_code)"
          @responder="
            (valor, interaccion) => cuestionario.responder(pregunta.field_code, valor, interaccion)
          "
          @no-sabe="cuestionario.noSabe(pregunta.field_code)"
        />
      </section>
    </template>

    <template #pie>
      <div v-if="resultado" class="pie">
        <button type="button" class="pie__enviar" @click="emitir('cerrar')">Listo</button>
      </div>

      <div v-else class="pie">
        <p v-if="errorEnvio" class="pie__error">{{ errorEnvio }}</p>
        <div class="pie__linea">
          <p class="pie__cuenta">
            <b>{{ contestadas }}</b> respondidas
          </p>
          <button
            type="button"
            class="pie__enviar"
            :disabled="contestadas === 0 || enviando"
            @click="enviar"
          >
            {{ enviando ? "Guardando…" : "Guardar cuestionario" }}
          </button>
        </div>
      </div>
    </template>
  </DialogoModal>
</template>

<style scoped>
.estado {
  padding: var(--faro-esp-12) var(--faro-esp-14);
  font-size: var(--faro-fs-125);
  color: var(--faro-gris-texto);
  background: var(--faro-superficie);
  border-radius: var(--faro-radio-14);
}

.estado + .estado {
  margin-top: var(--faro-esp-8);
}

.estado--fallo {
  color: var(--faro-critica-alta-texto);
  background: var(--faro-critica-alta-fondo);
}

.estado--aviso {
  color: var(--faro-critica-media-texto);
  background: var(--faro-critica-media-fondo);
}

.bloque + .bloque,
.estado + .bloque {
  margin-top: var(--faro-esp-14);
}

/*
 * Cada grupo es una tarjeta del mismo sistema que las de la pantalla de Salud:
 * superficie blanca, radio 24, elevación 1. Los campos van dentro, separados por
 * filete.
 */
.grupo {
  padding: var(--faro-esp-6) var(--faro-esp-16) var(--faro-esp-10);
  background: var(--faro-superficie);
  border-radius: var(--faro-radio-24);
  box-shadow: var(--faro-elev-1);
}

.grupo__titulo {
  padding-top: var(--faro-esp-14);
  font-size: var(--faro-fs-15);
  font-weight: 700;
  color: var(--faro-marca-profundo);
}

.grupo__subtitulo {
  margin-top: var(--faro-esp-4);
  font-size: var(--faro-fs-125);
  color: var(--faro-gris-texto);
}

.hecho {
  padding-block: var(--faro-esp-20);
  text-align: center;
}

.hecho__insignia {
  display: inline-grid;
  place-items: center;
  width: 56px;
  height: 56px;
  color: var(--faro-marca-accion);
  background: var(--faro-marca-icono-fondo);
  border-radius: 50%;
}

.hecho__tilde {
  width: var(--faro-icono-26);
  height: var(--faro-icono-26);
}

.hecho__titulo {
  margin-top: var(--faro-esp-14);
  font-size: var(--faro-fs-17);
  font-weight: 700;
  color: var(--faro-marca-profundo);
}

.hecho__detalle {
  margin-top: var(--faro-esp-6);
  font-size: var(--faro-fs-135);
  color: var(--faro-marca-texto);
}

.hecho__criticas {
  margin-top: var(--faro-esp-20);
  text-align: left;
}

.pie__linea {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--faro-esp-12);
}

.pie__cuenta {
  font-size: var(--faro-fs-125);
  color: var(--faro-gris-texto);
}

.pie__cuenta b {
  font-size: var(--faro-fs-15);
  color: var(--faro-marca-profundo);
}

.pie__error {
  margin-bottom: var(--faro-esp-10);
  font-size: var(--faro-fs-125);
  color: var(--faro-critica-alta-texto);
}

.pie__enviar {
  min-height: var(--faro-toque);
  padding-inline: var(--faro-esp-22);
  font-size: var(--faro-fs-135);
  font-weight: 700;
  color: var(--faro-superficie);
  background: var(--faro-marca-accion);
  border-radius: var(--faro-radio-pastilla);
  box-shadow: var(--faro-elev-1);
}

.pie__enviar:disabled {
  color: var(--faro-gris-texto);
  background: var(--faro-punto-inactivo);
  box-shadow: none;
  cursor: default;
}

.pie__enviar:focus-visible {
  outline: var(--faro-foco-grosor) solid var(--faro-foco-oscuro);
  outline-offset: var(--faro-foco-offset);
}

.pie > .pie__enviar {
  width: 100%;
}
</style>
