<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";

import type { FormSubmissionResponse } from "@/api/contrato";
import { BLUBATHON_TEXTS_ES } from "@/api/contrato";
import BotonAccion from "@/components/base/BotonAccion.vue";
import DialogoModal from "@/components/base/DialogoModal.vue";
import GloboAyuda from "@/components/base/GloboAyuda.vue";
import CampoCuestionario from "@/components/cuestionario/CampoCuestionario.vue";
import PortadaCuestionario from "@/components/cuestionario/PortadaCuestionario.vue";
import ResumenSugerencias from "@/components/cuestionario/ResumenSugerencias.vue";
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
  aPreguntar,
  sugerencias,
  sugerenciasPendientes,
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
 * preguntas sin desplazar. Por eso el corte se hace sobre `aPreguntar` y no
 * sobre ningún reparto temático: quien decide qué se pregunta primero sigue
 * siendo el plan del servidor, y quien decide el orden del resto sigue siendo
 * el orden canónico del catálogo.
 *
 * `aPreguntar` y no `enOrden`: lo que Blubathon ya aprendió no se pregunta, y
 * por tanto tampoco ocupa página.
 *
 * Tres, y no cuatro ni cinco, porque tres campos con su enunciado y sus
 * controles es lo que cabe en la hoja de un teléfono sin que haya que hacer
 * rodar la pantalla para ver si queda algo.
 * ------------------------------------------------------------------------- */

const POR_PAGINA = 3;

const pagina = ref(0);

const paginas = computed(() => Math.max(1, Math.ceil(aPreguntar.value.length / POR_PAGINA)));

const visibles = computed(() =>
  aPreguntar.value.slice(pagina.value * POR_PAGINA, pagina.value * POR_PAGINA + POR_PAGINA),
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

/* ---------------------------------------------------------------------------
 * El paso de revisión.
 *
 * Los campos que Blubathon ya aprendió no se preguntan —ver `aPreguntar`—, así
 * que al llegar aquí no se ha visto ninguno de sus valores. Esconderlos del
 * todo sería enviar por ti respuestas que nadie ha leído, así que la decisión
 * no desaparece: se toma una sola vez, al final, sobre la lista entera.
 *
 * Al guardar, si hay sugerencias sin decidir, en vez de enviar se enseña qué
 * son y se pregunta. Dos salidas y las dos acaban en un envío:
 *
 * - **Revisarlas** vuelve al formulario con esos campos abiertos y sus
 *   sugerencias a la vista, como estaban antes de esconderlas. Lo que no se
 *   cambie se acepta igual al guardar.
 * - **Enviar así** las acepta todas y guarda. Es el camino corto, y es el que
 *   está a un dedo de distancia.
 *
 * Cerrar el diálogo sin elegir no envía nada, que es lo que ya hacía antes.
 * ------------------------------------------------------------------------- */

type Paso = "formulario" | "revision";

const paso = ref<Paso>("formulario");

/** En revisión solo se ven los campos cuya sugerencia se pidió revisar. */
const soloSugeridas = ref(false);

const preguntasVisibles = computed(() =>
  soloSugeridas.value
    ? enOrden.value.filter((pregunta) => cuestionario.sugerenciaVisible(pregunta.field_code))
    : visibles.value,
);

async function guardar(): Promise<void> {
  // Se pregunta una sola vez: al volver de la revisión se guarda sin más, con
  // lo que se haya cambiado y lo que se haya dejado.
  if (
    paso.value === "formulario" &&
    !soloSugeridas.value &&
    sugerenciasPendientes.value.length > 0
  ) {
    paso.value = "revision";
    return;
  }
  await enviar();
}

/** "Revisarlas": el formulario vuelve, recortado a esas preguntas. */
async function revisar(): Promise<void> {
  cuestionario.revelarSugerencias();
  soloSugeridas.value = true;
  paso.value = "formulario";
  await nextTick();
  bloque.value?.scrollIntoView({ block: "start" });
}

/** "Enviar así": se aceptan tal cual y se guarda. */
async function aceptarYEnviar(): Promise<void> {
  cuestionario.aplicarSugerencias();
  await enviar();
}

/*
 * Los puntos de la portada solo cuentan páginas del formulario. En el repaso y
 * en la confirmación no se avanza por páginas, y unos puntos congelados ahí se
 * leerían como que algo se quedó a medias.
 */
const conProgreso = computed(
  () => resultado.value === null && paso.value === "formulario" && !soloSugeridas.value,
);

async function enviar(): Promise<void> {
  // Lo que quede sin tocar se acepta: es lo que se anunció en la revisión y lo
  // que se anuncia en el pie mientras se revisa.
  cuestionario.aplicarSugerencias();
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
    <template #portada="{ idTitulo }">
      <PortadaCuestionario
        :id-titulo="idTitulo"
        sobretitulo="Cuestionario diario"
        :titulo="titulo"
        :paso="pagina + 1"
        :pasos="conProgreso ? paginas : 0"
      >
        <!--
          Cómo funciona esto, en tres frases y sin jerga. No bloquea nada: se
          abre y se cierra cuando se quiera, a diferencia del diálogo de
          desregulación, que sí exige una respuesta antes de dejar seguir.
        -->
        <template #ayuda>
          <GloboAyuda
            etiqueta="Cómo funciona el cuestionario diario"
            titulo="Cómo funciona"
            lado="derecha"
          >
            <p>
              Cuenta cómo fue el día. No hace falta responder todo: se guarda lo que hayas puesto, y
              las preguntas van de tres en tres.
            </p>
            <p>
              Las primeras son las que más falta hacen hoy. Las que respondes casi siempre igual
              no se te preguntan: Blubathon las rellena por ti y te las enseña al final por si
              quieres cambiarlas.
            </p>
          </GloboAyuda>
        </template>
      </PortadaCuestionario>
    </template>

    <!-- Enviado: la confirmación ocupa el diálogo entero. -->
    <div v-if="resultado" class="hecho">
      <span class="hecho__insignia" aria-hidden="true">
        <IconoCheck class="hecho__tilde" />
      </span>
      <h3 class="hecho__titulo">Cuestionario guardado</h3>
      <p class="hecho__detalle">{{ MENSAJE_ENVIO[resultado.status] }}</p>
    </div>

    <!--
      La revisión. Primero qué se va a enviar, después la pregunta: quien lee
      llega a "¿quieres cambiarlas?" sabiendo ya de qué se le habla, que es lo
      único que hace que la pregunta se pueda contestar sin abrir nada.
    -->
    <div v-else-if="paso === 'revision'" class="revision">
      <h3 class="revision__titulo">Respuestas que se enviarán por ti</h3>
      <p class="revision__detalle">
        {{
          sugerenciasPendientes.length === 1
            ? "Esta no se te preguntó porque la respondes casi siempre igual"
            : "Estas no se te preguntaron porque las respondes casi siempre igual"
        }}. Blubathon las rellena con lo que sueles responder, a partir de tus últimos dos meses.
      </p>

      <ResumenSugerencias :sugerencias="sugerenciasPendientes" />

      <p class="revision__pregunta">¿Quieres cambiar alguna antes de guardar?</p>
    </div>

    <template v-else>
      <p v-if="cargando" class="estado">{{ BLUBATHON_TEXTS_ES.loadingEs }}</p>

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
        El formulario. Ya no es una tarjeta: es el cuerpo del diálogo, del mismo
        blanco, sin sombra y sin radio. Una tarjeta dentro de una hoja dibujaba
        un segundo plano que no significaba nada —lo único que hay aquí son
        preguntas—, y lo que separa una de otra sigue siendo el filete.

        Tampoco lleva ya un párrafo explicando cómo se recorre: eso está en el
        "(?)" de la portada, y aquí solo van la pregunta y sus respuestas.
      -->
      <section ref="bloque" class="bloque grupo">
        <!-- Al volver de la revisión el formulario ya no se pagina: son las
             preguntas que se pidió revisar y son todas las que hay. -->
        <template v-if="soloSugeridas">
          <h3 class="grupo__titulo">Lo que Blubathon responde por ti</h3>
          <p class="grupo__subtitulo">
            Cambia las que quieras. Las que dejes como están se guardan con el valor sugerido.
          </p>
        </template>

        <CampoCuestionario
          v-for="pregunta in preguntasVisibles"
          :key="pregunta.field_code"
          :pregunta="pregunta"
          :borrador="borradores[pregunta.field_code]"
          :sugerencia="sugerencias.get(pregunta.field_code)"
          :mostrar-sugerencia="cuestionario.sugerenciaVisible(pregunta.field_code)"
          @responder="
            (valor, interaccion) => cuestionario.responder(pregunta.field_code, valor, interaccion)
          "
        />
      </section>
    </template>

    <template #pie>
      <div v-if="resultado" class="pie">
        <BotonAccion bloque @click="emitir('cerrar')">Listo</BotonAccion>
      </div>

      <!--
        Las dos salidas de la revisión, y ninguna es un callejón. "Enviar así" es
        la llena porque es la que espera quien ya daba el formulario por
        terminado; "Revisarlas" está al lado, no escondida detrás de un enlace.
      -->
      <div v-else-if="paso === 'revision'" class="pie">
        <p v-if="errorEnvio" class="pie__error">{{ errorEnvio }}</p>

        <div class="revision__acciones">
          <BotonAccion variante="secundario" @click="revisar">Sí, revisarlas</BotonAccion>
          <BotonAccion :disabled="enviando" @click="aceptarYEnviar">
            {{ enviando ? "Guardando…" : "No, guardar así" }}
          </BotonAccion>
        </div>
      </div>

      <div v-else class="pie">
        <p v-if="errorEnvio" class="pie__error">{{ errorEnvio }}</p>

        <!--
          El paginador mueve por dentro del mismo formulario. No confirma ni
          descarta nada: lo contestado en un bloque sigue en el borrador al
          pasar al siguiente, y guardar está disponible desde el primero.
        -->
        <div v-if="!soloSugeridas" class="paginador">
          <BotonAccion
            variante="secundario"
            class="paginador__paso"
            :disabled="enPrimera"
            @click="irA(pagina - 1)"
          >
            <IconoChevron class="paginador__glifo paginador__glifo--atras" />
            Anterior
          </BotonAccion>

          <BotonAccion
            variante="secundario"
            class="paginador__paso"
            :disabled="enUltima"
            @click="irA(pagina + 1)"
          >
            Siguiente
            <IconoChevron class="paginador__glifo" />
          </BotonAccion>
        </div>

        <BotonAccion bloque grande :disabled="contestadas === 0 || enviando" @click="guardar">
          {{ enviando ? "Guardando…" : "Guardar cuestionario" }}
        </BotonAccion>
      </div>
    </template>
  </DialogoModal>
</template>

<style scoped>
.estado {
  padding: var(--blubathon-esp-12) var(--blubathon-esp-14);
  font-size: var(--blubathon-fs-125);
  color: var(--blubathon-gris-texto);
  background: var(--blubathon-fila-activa);
  border-radius: var(--blubathon-radio-14);
}

.estado + .estado {
  margin-top: var(--blubathon-esp-8);
}

.estado--fallo {
  color: var(--blubathon-critica-alta-texto);
  background: var(--blubathon-critica-alta-fondo);
}

.estado--aviso {
  color: var(--blubathon-critica-media-texto);
  background: var(--blubathon-critica-media-fondo);
}

.bloque + .bloque,
.estado + .bloque {
  margin-top: var(--blubathon-esp-14);
}

/*
 * Cada grupo es una tarjeta del mismo sistema que las de la pantalla de Salud:
 * superficie blanca, radio 24, elevación 1. Los campos van dentro, separados por
 * filete.
 */
/* Sin fondo, sin radio y sin sombra: el cuerpo del diálogo ya es blanco y esto
   es ese mismo blanco. Solo pone el acolchado. */
.grupo {
  padding-bottom: var(--blubathon-esp-10);
}

.grupo__titulo {
  font-size: var(--blubathon-fs-15);
  font-weight: 700;
  color: var(--blubathon-marca-profundo);
}

.grupo__subtitulo {
  margin-top: var(--blubathon-esp-4);
  font-size: var(--blubathon-fs-125);
  color: var(--blubathon-gris-texto);
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
  gap: var(--blubathon-esp-8);
  margin-bottom: var(--blubathon-esp-12);
}

/* La pastilla es la de `BotonAccion` —incluida la manera de apagarse en el
   primero y en el último—; aquí solo se aprieta, que son dos y van en una fila
   de teléfono. */
.paginador .paginador__paso {
  gap: var(--blubathon-esp-6);
  padding-inline: var(--blubathon-esp-14);
  font-size: var(--blubathon-fs-13);
}

.paginador__glifo {
  width: var(--blubathon-icono-14);
  height: var(--blubathon-icono-14);
}

.paginador__glifo--atras {
  transform: rotate(180deg);
}

/*
 * La revisión. Es una tarjeta del mismo sistema que el bloque de preguntas —no
 * un aviso, no una alerta— porque no ha pasado nada malo: el formulario está
 * terminado y esto es la última confirmación.
 */
.revision {
  padding-block: var(--blubathon-esp-6) var(--blubathon-esp-10);
}

.revision__titulo {
  font-size: var(--blubathon-fs-15);
  font-weight: 700;
  color: var(--blubathon-marca-profundo);
}

.revision__detalle {
  margin-top: var(--blubathon-esp-4);
  font-size: var(--blubathon-fs-125);
  line-height: 1.45;
  color: var(--blubathon-gris-texto);
}

/* La pregunta va debajo de la lista y con el peso del título: se lee después de
   saber de qué se está hablando, no antes. */
.revision__pregunta {
  margin-top: var(--blubathon-esp-16);
  font-size: var(--blubathon-fs-135);
  font-weight: 700;
  color: var(--blubathon-marca-profundo);
}

/* Envuelven en 320: dos áreas táctiles de 44 con su texto no caben en una fila
   de teléfono estrecho sin bajar del mínimo. */
.revision__acciones {
  display: flex;
  flex-wrap: wrap;
  gap: var(--blubathon-esp-12);
}

.revision__acciones > * {
  flex: 1 1 9rem;
}

.hecho {
  padding-block: var(--blubathon-esp-20);
  text-align: center;
}

.hecho__insignia {
  display: inline-grid;
  place-items: center;
  width: 56px;
  height: 56px;
  color: var(--blubathon-marca-accion);
  background: var(--blubathon-marca-icono-fondo);
  border-radius: 50%;
}

.hecho__tilde {
  width: var(--blubathon-icono-26);
  height: var(--blubathon-icono-26);
}

.hecho__titulo {
  margin-top: var(--blubathon-esp-14);
  font-size: var(--blubathon-fs-17);
  font-weight: 700;
  color: var(--blubathon-marca-profundo);
}

.hecho__detalle {
  margin-top: var(--blubathon-esp-6);
  font-size: var(--blubathon-fs-135);
  color: var(--blubathon-marca-texto);
}

.pie__error {
  margin-bottom: var(--blubathon-esp-10);
  font-size: var(--blubathon-fs-125);
  color: var(--blubathon-critica-alta-texto);
}
</style>
