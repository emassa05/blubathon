<script setup lang="ts">
import { computed, ref } from "vue";

import IconoCheck from "@/components/icons/IconoCheck.vue";
import IconoCerrar from "@/components/icons/IconoCerrar.vue";
import IconoDestello from "@/components/icons/IconoDestello.vue";
import type { RecommendationInstanceView, ReviewQueueResponse } from "@/api/contrato";
import { ETIQUETA_DECISION } from "@/types/terapeuta";

const props = defineProps<{
  cola: ReviewQueueResponse | null;
  cargando: boolean;
  error: string | null;
  /** Id de la recomendación cuya decisión se está enviando, si hay alguna. */
  enviando: string | null;
}>();

const emitir = defineEmits<{ decidir: [id: string, decision: "approved" | "rejected"] }>();

/** Qué elemento de la muestra se está mirando. Índice y no id: la cola se
 *  recarga entera después de decidir, y un id podría ya no estar. */
const indice = ref(0);

const items = computed<readonly RecommendationInstanceView[]>(() => props.cola?.items ?? []);

const actual = computed<RecommendationInstanceView | null>(
  () => items.value[Math.min(indice.value, Math.max(0, items.value.length - 1))] ?? null,
);

/**
 * "1 de cada N", con la N que declara el servidor.
 *
 * No está escrito a mano: el denominador viaja en la respuesta junto a la
 * versión de la política, así que el día que la muestra cambie de 5 a 10 esta
 * frase cambia sola en vez de quedarse mintiendo.
 */
const explicacion = computed(() => {
  const cola = props.cola;
  if (cola === null) return "";
  return `Se revisa 1 de cada ${cola.sample_denominator} recomendaciones (${cola.candidates} redactadas)`;
});

/** Ya decidida: la muestra sigue enseñándola, con su veredicto, hasta que se
 *  recargue. Sacarla al instante haría dudar de si el clic llegó a registrarse. */
const decidida = computed(() => actual.value?.review_decision ?? null);

function mover(paso: number): void {
  if (items.value.length === 0) return;
  indice.value = (indice.value + paso + items.value.length) % items.value.length;
}

function decidir(decision: "approved" | "rejected"): void {
  const item = actual.value;
  if (item === null) return;
  emitir("decidir", item.recommendation_instance_id, decision);
}
</script>

<template>
  <section class="revision" aria-labelledby="revision-titulo">
    <header class="revision__cabecera">
      <h2 id="revision-titulo" class="revision__titulo">
        <span class="revision__insignia" aria-hidden="true">
          <IconoDestello class="revision__destello" />
        </span>
        Recomendaciones de IA
      </h2>

      <p v-if="explicacion" class="revision__muestra">{{ explicacion }}</p>
    </header>

    <p v-if="cargando" class="revision__aviso" role="status">Cargando la cola de revisión…</p>

    <p v-else-if="error" class="revision__aviso" role="alert">{{ error }}</p>

    <!-- Cola vacía no es un fallo: puede que hoy no haya tocado ninguna en la
         muestra, y decirlo evita que se lea como que la API no responde. -->
    <p v-else-if="items.length === 0" class="revision__aviso">
      Ninguna recomendación de hoy entró en la muestra de revisión.
    </p>

    <template v-else-if="actual">
      <div class="tarjeta">
        <p class="tarjeta__nino">
          {{ actual.child_label ?? "Niño sin etiqueta" }}
          <span v-if="actual.local_date" class="tarjeta__fecha">· {{ actual.local_date }}</span>
        </p>

        <p class="tarjeta__accion">{{ actual.action_text_es }}</p>
        <p v-if="actual.purpose_es" class="tarjeta__proposito">{{ actual.purpose_es }}</p>

        <!--
          Las citas no son adorno: la recomendación solo existe si cada
          afirmación salió de un fragmento del corpus, y lo que el profesional
          está aprobando es exactamente eso. Sin la fuente delante, aprobar
          sería firmar a ciegas.
        -->
        <ul v-if="actual.citations?.length" class="citas">
          <li v-for="(cita, i) in actual.citations" :key="i" class="citas__cita">
            <p class="citas__texto">«{{ cita.quote_es }}»</p>
            <p class="citas__fuente">{{ cita.document_title_es }} · {{ cita.locator }}</p>
          </li>
        </ul>
      </div>

      <p v-if="decidida" class="veredicto" :class="`veredicto--${decidida}`" role="status">
        {{ ETIQUETA_DECISION[decidida] }}
      </p>

      <div class="acciones">
        <button
          type="button"
          class="boton boton--rechazar"
          :disabled="enviando !== null"
          @click="decidir('rejected')"
        >
          <IconoCerrar class="boton__icono" aria-hidden="true" />
          No aprobar
        </button>

        <button
          type="button"
          class="boton boton--aprobar"
          :disabled="enviando !== null"
          @click="decidir('approved')"
        >
          <IconoCheck class="boton__icono" aria-hidden="true" />
          Aprobar
        </button>
      </div>

      <!-- El paginador va debajo de las acciones: lo que se hace aquí es
           decidir, y pasar a la siguiente es lo que se hace después. -->
      <div v-if="items.length > 1" class="paginador">
        <button type="button" class="paginador__paso" aria-label="Anterior" @click="mover(-1)">
          ‹
        </button>
        <span class="paginador__posicion">
          {{ Math.min(indice + 1, items.length) }} de {{ items.length }}
        </span>
        <button type="button" class="paginador__paso" aria-label="Siguiente" @click="mover(1)">
          ›
        </button>
      </div>
    </template>
  </section>
</template>

<style scoped>
.revision {
  display: flex;
  flex-direction: column;
  gap: var(--blubathon-esp-12);
  padding: var(--blubathon-esp-18);
  background:
    radial-gradient(120% 130% at 0% 0%, var(--blubathon-marca-icono-fondo), transparent 58%),
    var(--blubathon-superficie);
  border-radius: var(--blubathon-radio-24);
  box-shadow: var(--blubathon-elev-1);
}

.revision__cabecera {
  display: flex;
  flex-wrap: wrap;
  gap: var(--blubathon-esp-8);
  align-items: center;
  justify-content: space-between;
}

.revision__titulo {
  display: flex;
  align-items: center;
  gap: var(--blubathon-esp-10);
  font-size: var(--blubathon-fs-11);
  font-weight: 700;
  letter-spacing: var(--blubathon-track-014);
  text-transform: uppercase;
  color: var(--blubathon-marca-texto);
}

.revision__insignia {
  display: grid;
  flex: none;
  place-items: center;
  width: var(--blubathon-caja-icono);
  height: var(--blubathon-caja-icono);
  background: var(--blubathon-marca-icono-fondo);
  border-radius: 50%;
}

.revision__destello {
  width: var(--blubathon-icono-14);
  height: var(--blubathon-icono-14);
}

/* La regla del muestreo se dice, no se supone. Una cola que no declara que es
   una muestra se lee como el trabajo entero del día. */
.revision__muestra {
  font-size: var(--blubathon-fs-11);
  color: var(--blubathon-gris-texto);
}

.revision__aviso {
  font-size: var(--blubathon-fs-135);
  color: var(--blubathon-gris-texto);
}

.tarjeta__nino {
  font-size: var(--blubathon-fs-12);
  font-weight: 700;
  letter-spacing: var(--blubathon-track-012);
  color: var(--blubathon-gris-texto);
}

.tarjeta__fecha {
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

.tarjeta__accion {
  margin-top: var(--blubathon-esp-8);
  font-size: var(--blubathon-fs-155);
  font-weight: 700;
  line-height: 1.4;
  color: var(--blubathon-marca-profundo);
}

.tarjeta__proposito {
  margin-top: var(--blubathon-esp-6);
  font-size: var(--blubathon-fs-13);
  line-height: 1.45;
  color: var(--blubathon-marca-texto);
}

.citas {
  margin-top: var(--blubathon-esp-12);
  list-style: none;
}

.citas__cita {
  padding-left: var(--blubathon-esp-10);
  border-left: 2px solid var(--blubathon-linea);
}

.citas__cita + .citas__cita {
  margin-top: var(--blubathon-esp-10);
}

.citas__texto {
  font-size: var(--blubathon-fs-12);
  font-style: italic;
  line-height: 1.45;
  color: var(--blubathon-marca-texto);
}

.citas__fuente {
  margin-top: 2px;
  font-size: var(--blubathon-fs-11);
  color: var(--blubathon-gris-texto);
}

.veredicto {
  padding: var(--blubathon-esp-8) var(--blubathon-esp-12);
  font-size: var(--blubathon-fs-12);
  font-weight: 700;
  border-radius: var(--blubathon-radio-10);
}

.veredicto--approved {
  color: var(--blubathon-marca-profundo);
  background: var(--blubathon-marca-icono-fondo);
}

.veredicto--rejected {
  color: var(--blubathon-alerta-texto);
  background: var(--blubathon-alerta-fondo);
}

/*
 * Los dos botones con el mismo peso visual. Aprobar no es la opción por defecto
 * ni la deseable: si el botón verde pesara más, la revisión derivaría en pulsar
 * el grande, que es justamente la fatiga de decisión que la muestra existe para
 * evitar.
 */
.acciones {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--blubathon-esp-10);
}

.boton {
  display: inline-flex;
  gap: var(--blubathon-esp-8);
  align-items: center;
  justify-content: center;
  min-height: var(--blubathon-toque);
  padding: 0 var(--blubathon-esp-14);
  font: inherit;
  font-size: var(--blubathon-fs-135);
  font-weight: 700;
  cursor: pointer;
  border: 1px solid transparent;
  border-radius: var(--blubathon-radio-pastilla);
}

.boton:disabled {
  cursor: progress;
  opacity: 0.55;
}

.boton:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-marca-accion);
  outline-offset: var(--blubathon-foco-offset);
}

.boton__icono {
  width: var(--blubathon-icono-14);
  height: var(--blubathon-icono-14);
}

.boton--aprobar {
  color: var(--blubathon-superficie);
  background: var(--blubathon-marca-accion);
}

.boton--rechazar {
  color: var(--blubathon-marca-texto);
  background: var(--blubathon-superficie);
  border-color: var(--blubathon-linea);
}

.paginador {
  display: flex;
  gap: var(--blubathon-esp-8);
  align-items: center;
  justify-content: center;
}

.paginador__paso {
  display: grid;
  place-items: center;
  width: var(--blubathon-toque);
  height: var(--blubathon-toque);
  font-size: var(--blubathon-fs-17);
  color: var(--blubathon-marca-texto);
  cursor: pointer;
  background: none;
  border: 0;
  border-radius: 50%;
}

.paginador__paso:hover {
  background: var(--blubathon-fila-activa);
}

.paginador__paso:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-marca-accion);
  outline-offset: calc(var(--blubathon-foco-offset) * -1);
}

.paginador__posicion {
  font-size: var(--blubathon-fs-12);
  color: var(--blubathon-gris-texto);
  font-variant-numeric: tabular-nums;
}
</style>
