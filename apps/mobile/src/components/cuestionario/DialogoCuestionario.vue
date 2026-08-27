<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";

import type { FormSubmissionResponse } from "@/api/contrato";
import { FARO_TEXTS_ES } from "@/api/contrato";
import DialogoModal from "@/components/base/DialogoModal.vue";
import CampoCuestionario from "@/components/cuestionario/CampoCuestionario.vue";
import IconoCheck from "@/components/icons/IconoCheck.vue";
import IconoChevron from "@/components/icons/IconoChevron.vue";
import { useCuestionario } from "@/composables/useCuestionario";
import { etiquetaDiaLargo } from "@/dominio/semana";
import { guardarRespuestas, respuestasDe } from "@/estado/respuestas";

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
});

const {
  cargando,
  error,
  enviando,
  errorEnvio,
  resultado,
  borradores,
  enOrden,
  sugerencias,
  contestadas,
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

/* ---------------------------------------------------------------------------
 * La paginación.
 *
 * El cuestionario es **un solo formulario** y sigue siéndolo: una lista de
 * preguntas, en un orden, con un borrador y un envío. Lo único que cambia aquí
 * es cuántas de esas preguntas se ven a la vez.
 *
 * No hay categorías. Un bloque no significa nada —no es "el sueño", no es "la
 * comida"—, es sencillamente dónde se cortó la lista para que quepan tres
 * preguntas sin desplazar. Por eso el corte se hace sobre `enOrden` y no sobre
 * ningún reparto temático: quien decide qué se pregunta primero sigue siendo el
 * plan del servidor, y quien decide el orden del resto sigue siendo el orden
 * canónico del catálogo.
 *
 * Tres, y no cuatro ni cinco, porque tres campos con su enunciado y sus
 * controles es lo que cabe en la hoja de un teléfono sin que haya que hacer
 * rodar la pantalla para ver si queda algo.
 * ------------------------------------------------------------------------- */

const POR_PAGINA = 3;

const pagina = ref(0);

const paginas = computed(() => Math.max(1, Math.ceil(enOrden.value.length / POR_PAGINA)));

const visibles = computed(() =>
  enOrden.value.slice(pagina.value * POR_PAGINA, pagina.value * POR_PAGINA + POR_PAGINA),
);

const enPrimera = computed(() => pagina.value === 0);
const enUltima = computed(() => pagina.value >= paginas.value - 1);

/*
 * El plan llega después del montaje y puede traer menos preguntas de las que
 * había con el catálogo entero: la página en la que se estaba puede dejar de
 * existir, y una página vacía no se lee como el final del formulario, se lee
 * como que se rompió.
 */
watch(paginas, (total) => {
  if (pagina.value > total - 1) pagina.value = total - 1;
});

const bloque = ref<HTMLElement | null>(null);

async function irA(destino: number): Promise<void> {
  pagina.value = Math.min(paginas.value - 1, Math.max(0, destino));
  // Las preguntas nuevas empiezan donde acabó el desplazamiento de las
  // anteriores: sin esto, un bloque se abre por la mitad de la primera.
  await nextTick();
  bloque.value?.scrollIntoView({ block: "start" });
}

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

      <!--
        La tarjeta del formulario. Es la misma de siempre —superficie, radio 24,
        elevación 1, campos separados por filete— y es una sola: lo que se
        recorre por dentro son sus preguntas, no una pila de tarjetas.
      -->
      <section ref="bloque" class="bloque grupo">
        <h3 class="grupo__titulo" aria-live="polite">Paso {{ pagina + 1 }} de {{ paginas }}</h3>
        <p class="grupo__subtitulo">
          Es un solo formulario: se recorre de tres en tres y se guarda lo que haya.
        </p>

        <div class="progreso" role="presentation">
          <span
            class="progreso__hecho"
            :style="{ inlineSize: `${((pagina + 1) / paginas) * 100}%` }"
          ></span>
        </div>

        <CampoCuestionario
          v-for="pregunta in visibles"
          :key="pregunta.field_code"
          :pregunta="pregunta"
          :borrador="borradores[pregunta.field_code]"
          :sugerencia="sugerencias.get(pregunta.field_code)"
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

        <!--
          El paginador mueve por dentro del mismo formulario. No confirma ni
          descarta nada: lo contestado en un bloque sigue en el borrador al
          pasar al siguiente, y guardar está disponible desde el primero.
        -->
        <div class="paginador">
          <button
            type="button"
            class="paginador__paso"
            :disabled="enPrimera"
            @click="irA(pagina - 1)"
          >
            <IconoChevron class="paginador__glifo paginador__glifo--atras" />
            Anterior
          </button>

          <button
            type="button"
            class="paginador__paso"
            :disabled="enUltima"
            @click="irA(pagina + 1)"
          >
            Siguiente
            <IconoChevron class="paginador__glifo" />
          </button>
        </div>

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

/*
 * Cuánto queda. Es una línea y no una fila de puntos: con dieciocho preguntas
 * el plan puede dar seis bloques, y seis puntos ya se cuentan de uno en uno en
 * vez de leerse de un vistazo.
 */
.progreso {
  overflow: hidden;
  height: var(--faro-esp-4);
  margin-top: var(--faro-esp-10);
  background: var(--faro-punto-inactivo);
  border-radius: var(--faro-radio-pastilla);
}

.progreso__hecho {
  display: block;
  block-size: 100%;
  background: var(--faro-marca-accion);
  border-radius: inherit;
}

/*
 * El paginador va sobre la línea de guardar y no en su misma fila: son dos
 * cosas distintas —moverse por el formulario y cerrarlo— y en una sola fila de
 * teléfono, con tres controles, la de guardar dejaría de ser la que destaca.
 *
 * Por eso los pasos son pastillas sin relleno: navegar es lo secundario, y el
 * único botón lleno del pie sigue siendo "Guardar cuestionario".
 */
.paginador {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--faro-esp-8);
  margin-bottom: var(--faro-esp-12);
}

.paginador__paso {
  display: inline-flex;
  align-items: center;
  gap: var(--faro-esp-6);
  min-height: var(--faro-toque);
  padding-inline: var(--faro-esp-14);
  font-size: var(--faro-fs-13);
  font-weight: 700;
  color: var(--faro-marca-accion);
  background: var(--faro-superficie);
  border: 1px solid var(--faro-linea);
  border-radius: var(--faro-radio-pastilla);
}

.paginador__paso:hover:not(:disabled) {
  border-color: var(--faro-punto-activo);
}

.paginador__paso:focus-visible {
  outline: var(--faro-foco-grosor) solid var(--faro-foco-oscuro);
  outline-offset: var(--faro-foco-offset);
}

/* En el primero y en el último no se desvanece: sigue ahí, apagado, para que
   el pie no cambie de forma al llegar a un extremo. */
.paginador__paso:disabled {
  color: var(--faro-punto-inactivo);
  cursor: default;
}

.paginador__glifo {
  width: var(--faro-icono-14);
  height: var(--faro-icono-14);
}

.paginador__glifo--atras {
  transform: rotate(180deg);
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
