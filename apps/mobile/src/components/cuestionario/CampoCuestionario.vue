<script setup lang="ts">
import { computed, ref, useId, watch } from "vue";

import type { DefaultSuggestion, FieldCode, FormQuestion, ValorCampo } from "@/api/contrato";
import { BLUBATHON_TEXTS_ES, type Interaccion } from "@/api/contrato";
import IconoCheck from "@/components/icons/IconoCheck.vue";
import IconoMas from "@/components/icons/IconoMas.vue";
import IconoMenos from "@/components/icons/IconoMenos.vue";
import {
  anclaOrdinal,
  escalaOrdinal,
  especificacionCampo,
  etiquetaCampo,
  etiquetaOpcion,
  formatearValor,
  preguntaCampo,
} from "@/dominio/campos";
import type { Borrador } from "@/composables/useCuestionario";

const props = withDefaults(
  defineProps<{
    pregunta: FormQuestion;
    borrador?: Borrador | undefined;
    sugerencia?: DefaultSuggestion | undefined;
    /**
     * Si la sugerencia se enseña.
     *
     * Por defecto **no**. La sugerencia sigue existiendo, sigue decidiendo el
     * `entry_mode` de lo que se conteste a mano y sigue llegando al envío si no
     * se toca el campo; lo que no hace ya es ocupar sitio en el formulario. Se
     * enseña solo cuando se pide revisarla al terminar.
     */
    mostrarSugerencia?: boolean;
  }>(),
  { borrador: undefined, sugerencia: undefined, mostrarSugerencia: false },
);

const emitir = defineEmits<{
  responder: [valor: ValorCampo, interaccion: Interaccion];
  noSabe: [];
}>();

const idControl = useId();
const idPregunta = useId();

const campo = computed<FieldCode>(() => props.pregunta.field_code);
const especificacion = computed(() => especificacionCampo(campo.value));
const etiqueta = computed(() => etiquetaCampo(campo.value));
const enunciado = computed(() => preguntaCampo(campo.value));

const valor = computed<ValorCampo | undefined>(() => props.borrador?.valor);
const noSabe = computed(() => props.borrador?.interaccion === "unknown");
const contestada = computed(() => props.borrador !== undefined);

/**
 * Con sugerencia sobre la mesa, responder a mano es editar la sugerencia: el
 * servidor deriva de ahí el `entry_mode`, y decirle "manual" cuando había una
 * presentación vigente falsearía la única señal que tiene para medir cuánto
 * ayudan las sugerencias.
 *
 * Mira la sugerencia y no si se está enseñando: la presentación es del servidor
 * y sigue vigente aunque la interfaz haya decidido no dibujarla. Atarlo a la
 * visibilidad convertiría un cambio de diseño en un cambio de dato.
 */
const interaccionManual = computed<Interaccion>(() =>
  props.sugerencia === undefined ? "manual" : "edit_default",
);

function responder(nuevo: ValorCampo): void {
  emitir("responder", nuevo, interaccionManual.value);
}

function aceptarSugerencia(): void {
  if (props.sugerencia === undefined) return;
  emitir("responder", props.sugerencia.value, "accept_default");
}

/* Opciones de un campo nominal, ya con su etiqueta del contrato. */
const opciones = computed(() =>
  (especificacion.value?.valores ?? []).map((valorPosible) => ({
    valor: valorPosible,
    etiqueta: etiquetaOpcion(campo.value, valorPosible),
  })),
);

const escala = computed(() =>
  especificacion.value === undefined ? [] : escalaOrdinal(especificacion.value),
);

const anclaSeleccionada = computed(() =>
  typeof valor.value === "number" ? anclaOrdinal(campo.value, valor.value) : "",
);

/* Números: el control es el campo de texto y los pasos solo lo ajustan. */
const paso = computed(() => (especificacion.value?.tipo === "continuous" ? 0.5 : 1));
const numero = ref<string>(typeof valor.value === "number" ? String(valor.value) : "");

watch(valor, (nuevo) => {
  const texto = typeof nuevo === "number" ? String(nuevo) : "";
  if (texto !== numero.value) numero.value = texto;
});

function acotar(bruto: number): number {
  const minimo = especificacion.value?.minimo ?? 0;
  const maximo = especificacion.value?.maximo ?? bruto;
  const dentro = Math.min(maximo, Math.max(minimo, bruto));
  // Los `count` y los `ordinal` son enteros en el contrato; redondear aquí evita
  // que un 3.5 escrito a mano llegue al servidor y lo rechace.
  return paso.value === 1 ? Math.round(dentro) : Math.round(dentro * 2) / 2;
}

function escribirNumero(evento: Event): void {
  const bruto = (evento.target as HTMLInputElement).value;
  numero.value = bruto;
  if (bruto.trim() === "") return;
  const convertido = Number(bruto);
  if (Number.isNaN(convertido)) return;
  responder(acotar(convertido));
}

function ajustar(direccion: number): void {
  const base = typeof valor.value === "number" ? valor.value : (especificacion.value?.minimo ?? 0);
  responder(acotar(base + direccion * paso.value));
}

const puedeAjustar = computed(() => typeof valor.value === "number");

/* Texto libre: se guarda al salir del campo, no en cada tecla. */
const texto = ref<string>(typeof valor.value === "string" ? valor.value : "");

function guardarTexto(): void {
  const limpio = texto.value.trim();
  if (limpio === "") return;
  responder(limpio);
}

const motivoDestacada = computed(() => {
  if (!props.pregunta.highlighted) return "";
  return props.pregunta.reason === "staleness"
    ? "Hace días que no se registra"
    : props.pregunta.reason === "exploration"
      ? "Toca revisarla hoy"
      : "";
});
</script>

<template>
  <fieldset class="campo" :data-campo="campo" :data-contestada="contestada">
    <legend class="campo__legenda">
      <span class="campo__titulo">{{ etiqueta }}</span>
      <span v-if="contestada" class="campo__hecho">
        <IconoCheck class="campo__tilde" aria-hidden="true" />
        <span class="oculto-visual">Contestada</span>
      </span>
    </legend>

    <p :id="idPregunta" class="campo__enunciado">{{ enunciado }}</p>
    <p v-if="motivoDestacada" class="campo__motivo">{{ motivoDestacada }}</p>

    <!-- La sugerencia es ayuda, no valor: se ve distinta y hay que aceptarla.
         Y solo se ve cuando se pidió revisarla —ver `mostrarSugerencia`. -->
    <div v-if="sugerencia && mostrarSugerencia" class="sugerencia">
      <p class="sugerencia__valor">
        Suele responder
        <b>{{ formatearValor(campo, sugerencia.value) }}</b>
      </p>
      <p class="sugerencia__ayuda">{{ BLUBATHON_TEXTS_ES.defaultSuggestionHintEs }}</p>
      <button type="button" class="sugerencia__usar" @click="aceptarSugerencia">
        Usar esta respuesta
      </button>
    </div>

    <!-- Sí / No -->
    <div v-if="especificacion?.tipo === 'boolean'" class="opciones" role="group">
      <button
        v-for="opcion in [true, false]"
        :key="String(opcion)"
        type="button"
        class="opcion"
        :class="{ 'opcion--activa': valor === opcion }"
        :aria-pressed="valor === opcion"
        @click="responder(opcion)"
      >
        {{ opcion ? "Sí" : "No" }}
      </button>
    </div>

    <!-- Una de varias -->
    <div v-else-if="especificacion?.tipo === 'nominal'" class="opciones" role="group">
      <button
        v-for="opcion in opciones"
        :key="opcion.valor"
        type="button"
        class="opcion"
        :class="{ 'opcion--activa': valor === opcion.valor }"
        :aria-pressed="valor === opcion.valor"
        @click="responder(opcion.valor)"
      >
        {{ opcion.etiqueta }}
      </button>
    </div>

    <!-- Escala de 1 a 5. Las anclas son del contrato y no se reescriben. -->
    <div v-else-if="especificacion?.tipo === 'ordinal'" class="escala">
      <div class="escala__puntos" role="group">
        <button
          v-for="punto in escala"
          :key="punto"
          type="button"
          class="escala__punto"
          :class="{ 'escala__punto--activo': valor === punto }"
          :aria-pressed="valor === punto"
          :aria-label="`${punto}. ${anclaOrdinal(campo, punto)}`"
          @click="responder(punto)"
        >
          {{ punto }}
        </button>
      </div>
      <p v-if="anclaSeleccionada" class="escala__ancla">{{ anclaSeleccionada }}</p>
    </div>

    <p v-else-if="especificacion?.tipo === 'tag_set'" class="campo__sin-catalogo">
      El catálogo de conductas todavía no está publicado, así que este campo no se pregunta. Lo que
      haya que contar de hoy cabe en las notas.
    </p>

    <!-- Notas -->
    <div v-else-if="especificacion?.tipo === 'text'" class="texto">
      <!-- El rótulo ya está en la leyenda del grupo: aquí se envuelve el control
           y se queda solo para el lector, sin repetirse en pantalla. -->
      <label class="envoltorio" :for="idControl">
        <span class="oculto-visual">{{ etiqueta }}</span>
        <textarea
          :id="idControl"
          v-model="texto"
          class="texto__area"
          rows="3"
          :maxlength="especificacion.largoMaximo"
          :aria-describedby="idPregunta"
          @blur="guardarTexto"
        ></textarea>
      </label>
      <p class="texto__cuenta">{{ texto.length }} / {{ especificacion.largoMaximo }}</p>
    </div>

    <!-- Números: horas de sueño, despertares, episodios -->
    <div v-else class="numero">
      <button
        type="button"
        class="numero__paso"
        :disabled="!puedeAjustar"
        :aria-label="`Bajar ${etiqueta.toLowerCase()}`"
        @click="ajustar(-1)"
      >
        <IconoMenos class="numero__glifo" />
      </button>

      <label class="envoltorio" :for="idControl">
        <span class="oculto-visual">{{ etiqueta }}</span>
        <input
          :id="idControl"
          class="numero__campo"
          type="number"
          inputmode="decimal"
          :min="especificacion?.minimo"
          :max="especificacion?.maximo"
          :step="paso"
          :value="numero"
          :aria-describedby="idPregunta"
          @input="escribirNumero"
        />
      </label>

      <button
        type="button"
        class="numero__paso"
        :disabled="!puedeAjustar"
        :aria-label="`Subir ${etiqueta.toLowerCase()}`"
        @click="ajustar(1)"
      >
        <IconoMas class="numero__glifo" />
      </button>
    </div>

    <div class="campo__cierre">
      <button
        type="button"
        class="opcion opcion--suave"
        :class="{ 'opcion--activa': noSabe }"
        :aria-pressed="noSabe"
        @click="emitir('noSabe')"
      >
        {{ BLUBATHON_TEXTS_ES.unknownAnswerEs }}
      </button>
      <p v-if="noSabe" class="campo__ayuda">{{ BLUBATHON_TEXTS_ES.unknownAnswerHintEs }}</p>
    </div>
  </fieldset>
</template>

<style scoped>
/*
 * Un campo es una fila de la tarjeta, no una tarjeta dentro de otra: dieciocho
 * cajas con sombra convierten el cuestionario en una lista de objetos y no en
 * una conversación. Separa el filete, igual que en las otras listas.
 */
.campo {
  padding-block: var(--blubathon-esp-16);
  border: 0;
}

.campo + .campo {
  border-top: 1px solid var(--blubathon-linea);
}

.campo__legenda {
  display: flex;
  align-items: center;
  gap: var(--blubathon-esp-8);
  /* `legend` en un `fieldset` sin borde: se comporta mejor como bloque normal. */
  float: left;
  width: 100%;
}

.campo__titulo {
  font-size: var(--blubathon-fs-135);
  font-weight: 700;
  color: var(--blubathon-marca-titulo);
}

.campo__hecho {
  display: grid;
  place-items: center;
  width: var(--blubathon-icono-16);
  height: var(--blubathon-icono-16);
  color: var(--blubathon-marca-accion);
}

.campo__tilde {
  width: var(--blubathon-icono-12);
  height: var(--blubathon-icono-12);
}

.campo__enunciado {
  clear: both;
  padding-top: var(--blubathon-esp-4);
  font-size: var(--blubathon-fs-125);
  color: var(--blubathon-gris-texto);
}

.campo__motivo {
  margin-top: var(--blubathon-esp-6);
  font-size: var(--blubathon-fs-11);
  font-weight: 700;
  letter-spacing: var(--blubathon-track-012);
  text-transform: uppercase;
  color: var(--blubathon-marca-accion);
}

.campo__sin-catalogo {
  margin-top: var(--blubathon-esp-10);
  font-size: var(--blubathon-fs-125);
  color: var(--blubathon-gris-texto);
}

.opciones {
  display: flex;
  flex-wrap: wrap;
  gap: var(--blubathon-esp-8);
  margin-top: var(--blubathon-esp-12);
}

/*
 * Una opción es una pastilla con área táctil completa. El estado seleccionado no
 * es solo color: el borde engorda y el texto se pone en negrita, para que se
 * distinga sin depender del tono.
 */
.opcion {
  min-height: var(--blubathon-toque);
  padding: var(--blubathon-esp-10) var(--blubathon-esp-16);
  font-size: var(--blubathon-fs-13);
  font-weight: 600;
  color: var(--blubathon-marca-texto);
  background: var(--blubathon-superficie);
  border: 1px solid var(--blubathon-linea);
  border-radius: var(--blubathon-radio-pastilla);
}

.opcion:hover {
  border-color: var(--blubathon-punto-activo);
}

.opcion:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-foco-oscuro);
  outline-offset: var(--blubathon-foco-offset);
}

.opcion--activa {
  font-weight: 700;
  color: var(--blubathon-marca-profundo);
  background: var(--blubathon-marca-icono-fondo);
  border-color: var(--blubathon-marca-accion);
  border-width: 2px;
}

.opcion--suave {
  font-weight: 600;
  color: var(--blubathon-gris-texto);
  background: none;
}

.escala {
  margin-top: var(--blubathon-esp-12);
}

.escala__puntos {
  display: flex;
  gap: var(--blubathon-esp-8);
}

/*
 * Los cinco puntos, con la cifra grande y el ancla debajo del grupo, no dentro
 * de cada botón: "Participó casi todo el tiempo" no cabe en 44px, y partirlo en
 * cinco columnas convierte la escala en un párrafo.
 */
.escala__punto {
  flex: 1;
  min-width: var(--blubathon-toque);
  min-height: var(--blubathon-toque);
  font-size: var(--blubathon-fs-15);
  font-weight: 700;
  color: var(--blubathon-marca-texto);
  background: var(--blubathon-superficie);
  border: 1px solid var(--blubathon-linea);
  border-radius: var(--blubathon-radio-14);
}

.escala__punto:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-foco-oscuro);
  outline-offset: var(--blubathon-foco-offset);
}

.escala__punto--activo {
  color: var(--blubathon-marca-profundo);
  background: var(--blubathon-marca-icono-fondo);
  border-color: var(--blubathon-marca-accion);
  border-width: 2px;
}

.escala__ancla {
  margin-top: var(--blubathon-esp-8);
  font-size: var(--blubathon-fs-125);
  font-weight: 600;
  color: var(--blubathon-marca-texto);
}

.numero {
  display: flex;
  align-items: center;
  gap: var(--blubathon-esp-10);
  margin-top: var(--blubathon-esp-12);
}

.numero__paso {
  display: grid;
  flex: none;
  place-items: center;
  width: var(--blubathon-toque);
  height: var(--blubathon-toque);
  color: var(--blubathon-marca-accion);
  background: var(--blubathon-superficie);
  border: 1px solid var(--blubathon-linea);
  border-radius: 50%;
}

.numero__paso:disabled {
  color: var(--blubathon-punto-inactivo);
  cursor: default;
}

.numero__paso:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-foco-oscuro);
  outline-offset: var(--blubathon-foco-offset);
}

.numero__glifo {
  width: var(--blubathon-icono-14);
  height: var(--blubathon-icono-14);
}

/* El rótulo envuelve al control para nombrarlo, pero no dibuja nada: con
   `display: contents` el control sigue siendo hijo directo de su fila. */
.envoltorio {
  display: contents;
}

.numero__campo {
  width: 6rem;
  min-height: var(--blubathon-toque);
  padding: var(--blubathon-esp-8) var(--blubathon-esp-12);
  font: inherit;
  font-size: var(--blubathon-fs-17);
  font-weight: 700;
  color: var(--blubathon-marca-profundo);
  text-align: center;
  background: var(--blubathon-superficie);
  border: 1px solid var(--blubathon-linea);
  border-radius: var(--blubathon-radio-14);
}

.numero__campo:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-foco-oscuro);
  outline-offset: var(--blubathon-foco-offset);
}

.texto {
  margin-top: var(--blubathon-esp-12);
}

.texto__area {
  width: 100%;
  padding: var(--blubathon-esp-12);
  font: inherit;
  font-size: var(--blubathon-fs-135);
  color: var(--blubathon-marca-texto);
  background: var(--blubathon-superficie);
  border: 1px solid var(--blubathon-linea);
  border-radius: var(--blubathon-radio-14);
  resize: vertical;
}

.texto__area:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-foco-oscuro);
  outline-offset: var(--blubathon-foco-offset);
}

.texto__cuenta {
  margin-top: var(--blubathon-esp-4);
  font-size: var(--blubathon-fs-11);
  color: var(--blubathon-gris-texto);
  text-align: right;
}

/* La sugerencia no puede parecer un valor ya puesto: fondo propio, borde
   discontinuo y su acción aparte. */
.sugerencia {
  margin-top: var(--blubathon-esp-12);
  padding: var(--blubathon-esp-12);
  background: var(--blubathon-marca-icono-fondo);
  border: 1px dashed var(--blubathon-marca-accion);
  border-radius: var(--blubathon-radio-14);
}

.sugerencia__valor {
  font-size: var(--blubathon-fs-125);
  color: var(--blubathon-marca-titulo);
}

.sugerencia__ayuda {
  margin-top: var(--blubathon-esp-4);
  font-size: var(--blubathon-fs-11);
  color: var(--blubathon-marca-texto);
}

.sugerencia__usar {
  min-height: var(--blubathon-toque);
  margin-top: var(--blubathon-esp-6);
  padding-inline: var(--blubathon-esp-14);
  font-size: var(--blubathon-fs-125);
  font-weight: 700;
  color: var(--blubathon-superficie);
  background: var(--blubathon-marca-accion);
  border-radius: var(--blubathon-radio-pastilla);
}

.sugerencia__usar:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-foco-oscuro);
  outline-offset: var(--blubathon-foco-offset);
}

.campo__cierre {
  margin-top: var(--blubathon-esp-10);
}

.campo__ayuda {
  margin-top: var(--blubathon-esp-6);
  font-size: var(--blubathon-fs-11);
  color: var(--blubathon-gris-texto);
}
</style>
