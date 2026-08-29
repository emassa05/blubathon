<script setup lang="ts">
import { computed, ref, useId, watch } from "vue";

import type { DefaultSuggestion, FieldCode, FormQuestion, ValorCampo } from "@/api/contrato";
import type { Interaccion } from "@/api/contrato";
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
}>();

const idControl = useId();
const idPregunta = useId();

const campo = computed<FieldCode>(() => props.pregunta.field_code);
const especificacion = computed(() => especificacionCampo(campo.value));
const etiqueta = computed(() => etiquetaCampo(campo.value));
const enunciado = computed(() => preguntaCampo(campo.value));

const valor = computed<ValorCampo | undefined>(() => props.borrador?.valor);
const contestada = computed(() => props.borrador !== undefined);

/**
 * Lo que se ve marcado.
 *
 * En el repaso la sugerencia sale ya elegida: por algo es una sugerencia, y
 * obligar a confirmarla con un botón pedía dos gestos para el caso normal
 * —dejarla como está— y ninguno para el excepcional.
 *
 * Marcarla no es guardarla. El borrador sigue sin tocarse y el campo sigue sin
 * contar como contestado, que es lo que separa `accept_default` de `manual`:
 * si no se toca, `aplicarSugerencias` la envía al guardar como `accept_default`
 * igual que antes; si se elige otra cosa, entra como `edit_default`. Lo que
 * cambia es lo que se ve, no lo que viaja.
 */
const marcado = computed<ValorCampo | undefined>(() =>
  valor.value !== undefined
    ? valor.value
    : props.mostrarSugerencia
      ? props.sugerencia?.value
      : undefined,
);

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
  typeof marcado.value === "number" ? anclaOrdinal(campo.value, marcado.value) : "",
);

/* Números: el control es el campo de texto y los pasos solo lo ajustan. */
const paso = computed(() => (especificacion.value?.tipo === "continuous" ? 0.5 : 1));
const numero = ref<string>(typeof valor.value === "number" ? String(valor.value) : "");

/*
 * La cifra con la que cuenta el control, que no es siempre la que trae la prop.
 *
 * Cada paso se calculaba sobre `props.borrador`, y el borrador da la vuelta por
 * el padre: se emite, el padre reescribe el mapa de borradores y Vue repinta al
 * hijo. Hasta que ese repintado no ocurre, la prop vale lo de antes. Dos
 * pulsaciones seguidas —lo normal para subir de 1 a 6— caen dentro de la misma
 * ventana y las dos leen la misma base: la segunda recalcula el valor que ya
 * había y se pierde. Desde fuera el paso se ve irregular, y al bajar igual.
 *
 * Contando aquí, cada pulsación parte de la anterior y ninguna depende de
 * cuándo repinte el padre. La prop sigue mandando cuando cambia por su cuenta
 * —se acepta una sugerencia, se reabre un día ya enviado—, que es el `watch`.
 */
const cifra = ref<number | undefined>(typeof valor.value === "number" ? valor.value : undefined);

watch(valor, (nuevo) => {
  cifra.value = typeof nuevo === "number" ? nuevo : undefined;
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
  // La coma decimal es la de aquí. Con `type="number"` el navegador ya la
  // traducía; en `text` llega tal cual y `Number("2,5")` es `NaN`, que se
  // descartaría en silencio dejando el campo escrito y el valor sin cambiar.
  const convertido = Number(bruto.replace(",", "."));
  if (Number.isNaN(convertido)) return;
  const acotado = acotar(convertido);
  cifra.value = acotado;
  responder(acotado);
}

/*
 * Una pulsación, un paso.
 *
 * Contar sobre `cifra` arregla las pulsaciones que se perdían, pero abre lo
 * contrario: si el mismo gesto llega más de una vez, todas suman. Y llega más de
 * una vez por dos caminos distintos, que piden dos redes distintas:
 *
 * - **Dentro del mismo despacho.** Un oyente que quedó duplicado entrega las dos
 *   llamadas seguidas, síncronas. `atendiendo` se levanta al atender y se baja
 *   en el microtask siguiente: lo del mismo despacho cae dentro, y dos
 *   pulsaciones de verdad, que son dos tareas, siguen contando las dos.
 *
 * - **En despachos distintos pero pegados.** El rebote de un interruptor o un
 *   clic de compatibilidad llegan como eventos separados, así que el microtask
 *   ya se vació entre medias y la marca de arriba no los ve. Ahí hay que mirar
 *   el reloj del propio evento: es el síntoma de que despacio va bien y deprisa
 *   sube de dos en dos, porque el rebote solo aparece cuando se pulsa rápido.
 *
 * El umbral es 40 ms. Un dedo no baja dos veces en ese hueco —quien más rápido
 * pulsa ronda los 100—, y un rebote vive por debajo de 30. Lo que llegue antes
 * es el mismo gesto contado dos veces, no dos gestos.
 *
 * El sello lo pone el navegador en el propio evento, así que es su reloj y no
 * el nuestro: no hay temporizador que mantener ni que limpiar al desmontar.
 */
const REBOTE_MS = 40;

let atendiendo = false;
let selloAtendido = Number.NEGATIVE_INFINITY;

function ajustar(direccion: number, evento?: MouseEvent): void {
  if (atendiendo) return;

  if (evento !== undefined) {
    if (evento.timeStamp - selloAtendido < REBOTE_MS) return;
    selloAtendido = evento.timeStamp;
  }

  atendiendo = true;
  queueMicrotask(() => {
    atendiendo = false;
  });

  const base = cifra.value ?? especificacion.value?.minimo ?? 0;
  const siguiente = acotar(base + direccion * paso.value);
  // Se apunta antes de emitir: la pulsación siguiente cuenta desde aquí aunque
  // el padre todavía no haya repintado.
  cifra.value = siguiente;
  numero.value = String(siguiente);
  responder(siguiente);
}

const puedeAjustar = computed(() => cifra.value !== undefined);

/* Texto libre: se guarda al salir del campo, no en cada tecla. */
const texto = ref<string>(typeof valor.value === "string" ? valor.value : "");

function guardarTexto(): void {
  const limpio = texto.value.trim();
  if (limpio === "") return;
  responder(limpio);
}

/*
 * Un solo tono, el verde de siempre.
 *
 * Hubo un azul aparte para el repaso, con la idea de decir "esto no lo elegiste
 * tú". Pero al lado de las respuestas verdes de las demás preguntas se leía como
 * otra cosa distinta y no como la misma fila en otro momento, y quien repasa ya
 * sabe lo que está repasando: lo dice el título del bloque y lo dice el renglón
 * de encima de cada pregunta. Con el verde, elegir y repasar se ven igual porque
 * son lo mismo: la respuesta que va a viajar.
 */
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

    <!-- Por qué la respuesta de abajo viene ya marcada. Es lo único que
         distingue una sugerencia de algo que se contestó, así que se dice con
         palabras y no con un color aparte —ver `marcado`. -->
    <p v-if="sugerencia && mostrarSugerencia" class="sugerencia">
      Suele responder
      <b class="sugerencia__dato">{{ formatearValor(campo, sugerencia.value) }}</b>
    </p>

    <!-- Sí / No -->
    <div v-if="especificacion?.tipo === 'boolean'" class="opciones" role="group">
      <OpcionRespuesta
        v-for="opcion in [true, false]"
        :key="String(opcion)"
        :etiqueta="opcion ? 'Sí' : 'No'"
        :marcada="marcado === opcion"
        @click="responder(opcion)"
      />
    </div>

    <!-- Una de varias -->
    <div v-else-if="especificacion?.tipo === 'nominal'" class="opciones" role="group">
      <OpcionRespuesta
        v-for="opcion in opciones"
        :key="opcion.valor"
        :etiqueta="opcion.etiqueta"
        :marcada="marcado === opcion.valor"
        @click="responder(opcion.valor)"
      />
    </div>

    <!-- Escala de 1 a 5. Las anclas son del contrato y no se reescriben. -->
    <div v-else-if="especificacion?.tipo === 'ordinal'" class="escala">
      <div class="escala__puntos" role="group">
        <button
          v-for="punto in escala"
          :key="punto"
          type="button"
          class="escala__punto"
          :class="{ 'escala__punto--activo': marcado === punto }"
          :aria-pressed="marcado === punto"
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
        @click="ajustar(-1, $event)"
      >
        <IconoMenos class="numero__glifo" />
      </button>

      <label class="envoltorio" :for="idControl">
        <span class="oculto-visual">{{ etiqueta }}</span>
        <!--
          `text` y no `number`, aunque el dato lo sea.

          Un `input type="number"` trae dos controles de regalo que aquí no
          pinta nadie: las flechitas nativas dentro del propio campo, que son
          parte del campo y no se distinguen de él, y el paso con la rueda del
          ratón cuando está enfocado. Lo segundo es el que muerde: se enfoca el
          campo, se sigue leyendo el formulario y al desplazar la página la
          cifra cambia sola, unas veces uno y otras dos. Desde fuera se ve como
          que los botones + y − suman de más o de menos.

          En `text` no hay flechas ni rueda, y los dos pasos del lado son la
          única manera de mover la cifra. `inputmode` mantiene el teclado
          numérico en el móvil, y lo que se escriba lo sigue acotando `acotar`
          contra el rango del catálogo, igual que antes.
        -->
        <input
          :id="idControl"
          class="numero__campo"
          type="text"
          inputmode="decimal"
          autocomplete="off"
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
        @click="ajustar(1, $event)"
      >
        <IconoMas class="numero__glifo" />
      </button>
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

/*
 * El renglón que avisa de que la respuesta de abajo la pone Blubathon.
 *
 * Antes esto era una caja: borde discontinuo, relleno azul, dos párrafos y una
 * pastilla verde dentro para aceptarla. Cuatro señales para lo mismo, y la
 * aceptación pedía un gesto justo para el caso que no lo necesita —dejarla como
 * está—. Ahora la respuesta ya viene marcada abajo con el verde de todas, y
 * aquí solo queda la frase que dice de dónde sale, pequeña y al margen.
 */
.sugerencia {
  clear: both;
  margin-top: var(--blubathon-esp-24);
  padding-left: var(--blubathon-esp-10);
  font-size: var(--blubathon-fs-125);
  color: var(--blubathon-gris-texto);
  border-left: 2px solid var(--blubathon-linea);
}

.sugerencia__dato {
  font-weight: 700;
  color: var(--blubathon-marca-texto);
}</style>
