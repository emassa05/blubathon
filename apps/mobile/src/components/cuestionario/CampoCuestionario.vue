<script setup lang="ts">
import { computed, ref, useId, watch } from "vue";

import type { DefaultSuggestion, FieldCode, FormQuestion, ValorCampo } from "@/api/contrato";
import { BLUBATHON_TEXTS_ES, type Interaccion } from "@/api/contrato";
import BotonAccion from "@/components/base/BotonAccion.vue";
import OpcionRespuesta from "@/components/base/OpcionRespuesta.vue";
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

/*
 * El tono de lo marcado. Mientras se contesta, verde: es lo que ha elegido quien
 * responde. En el repaso, azul: es lo que se va a enviar por él. Se mira lo
 * mismo que decide si la sugerencia se enseña, porque es exactamente el mismo
 * momento —ver `mostrarSugerencia`.
 */
const tono = computed<"eleccion" | "repaso">(() =>
  props.mostrarSugerencia ? "repaso" : "eleccion",
);
</script>

<template>
  <fieldset class="campo" :data-campo="campo" :data-contestada="contestada">
    <!--
      La pregunta y nada más.

      Antes había tres renglones por campo: el rótulo ("Calidad del sueño"), la
      pregunta, y a veces por qué se preguntaba hoy ("Hace días que no se
      registra"). Los tres decían lo mismo con distintas palabras y el rótulo lo
      decía peor, así que se queda la pregunta, que es lo único que hay que leer
      para contestar. El rótulo sigue existiendo donde hace falta: nombra cada
      control para el lector, ahí abajo, sin ocupar pantalla.
    -->
    <legend class="campo__legenda">
      <span :id="idPregunta" class="campo__pregunta">{{ enunciado }}</span>
    </legend>

    <!-- La sugerencia es ayuda, no valor: se ve distinta y hay que aceptarla.
         Y solo se ve cuando se pidió revisarla —ver `mostrarSugerencia`. -->
    <div v-if="sugerencia && mostrarSugerencia" class="sugerencia">
      <p class="sugerencia__valor">
        Suele responder
        <b>{{ formatearValor(campo, sugerencia.value) }}</b>
      </p>
      <p class="sugerencia__ayuda">{{ BLUBATHON_TEXTS_ES.defaultSuggestionHintEs }}</p>
      <BotonAccion class="sugerencia__usar" @click="aceptarSugerencia">
        Usar esta respuesta
      </BotonAccion>
    </div>

    <!-- Sí / No -->
    <div v-if="especificacion?.tipo === 'boolean'" class="opciones" role="group">
      <OpcionRespuesta
        v-for="opcion in [true, false]"
        :key="String(opcion)"
        :etiqueta="opcion ? 'Sí' : 'No'"
        :marcada="valor === opcion"
        :tono="tono"
        @click="responder(opcion)"
      />
    </div>

    <!-- Una de varias -->
    <div v-else-if="especificacion?.tipo === 'nominal'" class="opciones" role="group">
      <OpcionRespuesta
        v-for="opcion in opciones"
        :key="opcion.valor"
        :etiqueta="opcion.etiqueta"
        :marcada="valor === opcion.valor"
        :tono="tono"
        @click="responder(opcion.valor)"
      />
    </div>

    <!-- Escala de 1 a 5. Las anclas son del contrato y no se reescriben. -->
    <div v-else-if="especificacion?.tipo === 'ordinal'" class="escala">
      <div class="escala__puntos" :class="`escala__puntos--${tono}`" role="group">
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
      <!-- No es una opción más: es la salida de la pregunta. Por eso no lleva la
           fila entera con su marca, sino una pastilla suelta y más pequeña. -->
      <button
        type="button"
        class="no-se"
        :class="{ 'no-se--activo': noSabe }"
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
  /* El mismo acolchado arriba y abajo en todas: entre una pregunta y la
     siguiente hay siempre el mismo hueco, y es mayor que el que hay dentro de
     una —ver el margen de las respuestas—, que es lo que agrupa cada pregunta
     con lo suyo. */
  padding-block: var(--blubathon-esp-24);
  border: 0;
}

.campo + .campo {
  border-top: 1px solid var(--blubathon-linea);
}

.campo__legenda {
  /* `legend` en un `fieldset` sin borde: se comporta mejor como bloque normal. */
  float: left;
  width: 100%;
}

/* La única línea de texto del campo, y por eso se lee como un enunciado y no
   como el rótulo de un formulario: grande, al principio de la línea y con el
   color de los títulos. Lo que la separa de las respuestas es el margen de
   estas —esp-32—, cuatro veces el hueco entre una respuesta y la siguiente:
   primero se lee la pregunta, después se elige. */
.campo__pregunta {
  display: block;
  font-size: var(--blubathon-fs-17);
  font-weight: 700;
  line-height: 1.35;
  color: var(--blubathon-marca-titulo);
  text-align: start;
}

.campo__sin-catalogo {
  clear: both;
  margin-top: var(--blubathon-esp-10);
  font-size: var(--blubathon-fs-125);
  color: var(--blubathon-gris-texto);
}

/* Una opción por renglón, no en fila: las etiquetas del contrato son frases
   —"Interrumpido varias veces"— y en fila daban pastillas de anchos muy
   distintos que había que leer de reojo. La opción en sí es `OpcionRespuesta`. */
.opciones {
  clear: both;
  display: grid;
  gap: var(--blubathon-esp-8);
  margin-top: var(--blubathon-esp-32);
}

/* La salida de la pregunta, no una respuesta: pastilla suelta, apagada y del
   ancho de su texto. Al marcarse toma el mismo verde que lo elegido, porque
   marcado sí es una respuesta —viaja como `unknown`. */
.no-se {
  min-height: var(--blubathon-toque);
  padding: var(--blubathon-esp-10) var(--blubathon-esp-18);
  font-size: var(--blubathon-fs-13);
  font-weight: 600;
  color: var(--blubathon-gris-texto);
  background: var(--blubathon-opcion-fondo);
  border-radius: var(--blubathon-radio-pastilla);
}

.no-se:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-foco-oscuro);
  outline-offset: var(--blubathon-foco-offset);
}

.no-se--activo {
  font-weight: 700;
  color: var(--blubathon-opcion-texto-fuerte);
  background: var(--blubathon-opcion-elegida-fondo);
  box-shadow: var(--blubathon-elev-1);
}

.escala {
  clear: both;
  margin-top: var(--blubathon-esp-32);
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
  min-height: 52px;
  font-size: var(--blubathon-fs-15);
  font-weight: 600;
  color: var(--blubathon-opcion-texto);
  background: var(--blubathon-opcion-fondo);
  border-radius: var(--blubathon-radio-pastilla);
}

.escala__punto:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-foco-oscuro);
  outline-offset: var(--blubathon-foco-offset);
}

/* Los mismos dos tonos que las opciones de fila, por lo mismo: verde es lo que
   se eligió y azul lo que se va a enviar por ti. */
.escala__punto--activo {
  font-weight: 700;
  color: var(--blubathon-opcion-texto-fuerte);
  background: var(--blubathon-opcion-elegida-fondo);
  box-shadow: var(--blubathon-elev-1);
}

.escala__puntos--repaso .escala__punto--activo {
  color: var(--blubathon-opcion-repaso-texto);
  background: var(--blubathon-opcion-repaso-fondo);
}

.escala__ancla {
  margin-top: var(--blubathon-esp-8);
  font-size: var(--blubathon-fs-125);
  font-weight: 600;
  color: var(--blubathon-marca-texto);
}

/* Lo único que se queda en el centro: la cifra con sus dos pasos a los lados es
   un control simétrico, y arrimarlo al margen lo dejaría cojo. */
.numero {
  clear: both;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--blubathon-esp-10);
  margin-top: var(--blubathon-esp-32);
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
  clear: both;
  margin-top: var(--blubathon-esp-32);
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
   discontinuo y su acción aparte. Azul, como lo marcado del repaso: es la misma
   cosa contada dos veces —esto es lo que Blubathon enviaría por ti. */
.sugerencia {
  clear: both;
  margin-top: var(--blubathon-esp-32);
  padding: var(--blubathon-esp-12);
  background: var(--blubathon-opcion-repaso-fondo);
  border: 1px dashed var(--blubathon-opcion-repaso-texto);
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

/* Solo su sitio: la pastilla la pone `BotonAccion`, que es la de todos. */
.sugerencia__usar {
  margin-top: var(--blubathon-esp-10);
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
