<script setup lang="ts">
import { computed, ref } from "vue";

import type { RecommendationInstanceView, ReviewQueueResponse } from "@/api/contrato";
import IconoChevron from "@/components/icons/IconoChevron.vue";
import IconoDestello from "@/components/icons/IconoDestello.vue";
import TarjetaRevision from "@/components/terapeuta/TarjetaRevision.vue";
import type { FichaNino } from "@/types/terapeuta";

const props = defineProps<{
  cola: ReviewQueueResponse | null;
  cargando: boolean;
  error: string | null;
  /** Id de la recomendación cuya decisión se está enviando, si hay alguna. */
  enviando: string | null;
  /** La cartera, solo para poner cifra al riesgo de cada niño de la cola. */
  fichas: readonly FichaNino[];
}>();

defineEmits<{
  decidir: [id: string, decision: "approved" | "rejected"];
  verPerfil: [id: string];
}>();

/**
 * Cuántas se ven sin desplegar.
 *
 * Dos, y no las cinco de la muestra: el widget comparte columna con el resumen
 * del conjunto, y una lista de cinco tarjetas con sus citas y sus botones deja
 * el resto de la pantalla fuera de vista sin que nadie lo haya pedido.
 */
const A_LA_VISTA = 2;

const desplegado = ref(false);

const items = computed<readonly RecommendationInstanceView[]>(() => props.cola?.items ?? []);

const primeras = computed(() => items.value.slice(0, A_LA_VISTA));
const restantes = computed(() => items.value.slice(A_LA_VISTA));

const respondidas = computed(
  () => items.value.filter((item) => (item.review_decision ?? null) !== null).length,
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
  return `Se revisa 1 de cada ${cola.sample_denominator} · ${cola.candidates} redactadas · ${respondidas.value} respondidas`;
});

/** El riesgo del niño al que apunta la recomendación, si está en la cartera. */
function riesgoDe(item: RecommendationInstanceView): number | null {
  return props.fichas.find((ficha) => ficha.id === item.child_id)?.riesgo ?? null;
}
</script>

<template>
  <section
    class="revision"
    :class="{ 'revision--desplegada': desplegado }"
    aria-labelledby="revision-titulo"
  >
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

    <template v-else>
      <!--
        Dos grupos con su propio desplazamiento y no una sola lista larga. Las
        de arriba son las que tocan ahora; las de abajo, la cola que queda. Con
        un solo `overflow`, bajar a mirar la quinta hace desaparecer las dos
        primeras, y el widget deja de decir por dónde iba la revisión.
      -->
      <div class="revision__cuerpo">
        <ul class="grupo grupo--primeras">
          <li v-for="item in primeras" :key="item.recommendation_instance_id" class="grupo__item">
            <TarjetaRevision
              :item="item"
              :riesgo="riesgoDe(item)"
              :enviando="enviando !== null"
              @decidir="(id, decision) => $emit('decidir', id, decision)"
              @ver-perfil="(id) => $emit('verPerfil', id)"
            />
          </li>
        </ul>

        <section v-if="desplegado && restantes.length > 0" class="grupo grupo--restantes">
          <h3 class="grupo__titulo">Más pendientes ({{ restantes.length }})</h3>

          <ul class="grupo__lista">
            <li
              v-for="item in restantes"
              :key="item.recommendation_instance_id"
              class="grupo__item"
            >
              <TarjetaRevision
                :item="item"
                :riesgo="riesgoDe(item)"
                :enviando="enviando !== null"
                @decidir="(id, decision) => $emit('decidir', id, decision)"
                @ver-perfil="(id) => $emit('verPerfil', id)"
              />
            </li>
          </ul>
        </section>
      </div>

      <!--
        Abajo y centrado, y con aspecto de enlace y no de botón: desplegar no es
        una de las acciones de la pantalla —las acciones son los dos botones de
        cada tarjeta— y un tercer botón de tamaño parecido competiría con ellos.
      -->
      <button
        v-if="restantes.length > 0"
        type="button"
        class="revision__ver"
        :aria-expanded="desplegado"
        @click="desplegado = !desplegado"
      >
        {{ desplegado ? "Ver menos" : "Ver más" }}
        <IconoChevron
          class="revision__chevron"
          :class="desplegado ? 'revision__chevron--arriba' : 'revision__chevron--abajo'"
        />
      </button>
    </template>
  </section>
</template>

<style scoped>
/*
 * El widget ocupa entera la casilla que le da la pantalla y nunca más: quien
 * decide su altura es la retícula de `TerapeutaView`, y lo que sobra se
 * desplaza por dentro. Por eso aquí no hay ni una medida en `dvh` —la tenía, y
 * era una resta a ojo de la cabecera que se equivocaba en cuanto aparecía un
 * aviso.
 *
 * En móvil la casilla no tiene altura fija: el widget mide lo que mide su
 * contenido, ningún `overflow` de dentro llega a activarse y la página se
 * desplaza como siempre.
 */
.revision {
  display: flex;
  flex-direction: column;
  gap: var(--blubathon-esp-14);
  min-block-size: 0;
  padding: var(--blubathon-esp-18);
  /*
   * El azul de la pantalla de Salud, burbujas incluidas: es la superficie sobre
   * la que el cuidador lee estos mismos textos, y aquí dice de un vistazo cuál
   * de los tres widgets del panel es el que escribe la IA. Blanco, la cola solo
   * se distinguía de la cartera y del resumen por su rótulo.
   *
   * El lavado de la banda sigue viviendo dentro, en cada recomendación, y ahora
   * se ve mejor que antes: las tarjetas son lo único blanco del widget.
   */
  background: var(--blubathon-ia-superficie);
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
  /* Azulado, como el de la recomendación en la pantalla del cuidador: el disco
     de la marca es lo que dice que esto lo escribe la IA, y en blanco se leía
     como un icono suelto sobre el fondo. */
  background: var(--blubathon-ia-insignia);
  border-radius: 50%;
}

.revision__destello {
  width: var(--blubathon-icono-14);
  height: var(--blubathon-icono-14);
  /* No hereda el color del rótulo: el destello es azul sobre su disco azul,
     como en Salud, y no un icono del mismo gris que el texto de al lado. */
  color: var(--blubathon-marca-icono);
}

/* La regla del muestreo se dice, no se supone. Una cola que no declara que es
   una muestra se lee como el trabajo entero del día. */
.revision__muestra {
  font-size: var(--blubathon-fs-11);
  /* Sobre el azul, no sobre blanco: `gris-texto` se queda en 4.1:1 contra la
     burbuja más oscura y esta línea es de 11px. */
  color: var(--blubathon-ia-texto-suave);
}

.revision__aviso {
  font-size: var(--blubathon-fs-135);
  color: var(--blubathon-ia-texto-suave);
}

.revision__cuerpo {
  display: flex;
  flex-direction: column;
  gap: var(--blubathon-esp-14);
  min-block-size: 0;
}

.revision__cuerpo {
  flex: 1;
}

.grupo {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: var(--blubathon-esp-12);
  min-block-size: 0;
}

/*
 * Desplegado, el alto se reparte en 40/60 y no en proporción al contenido.
 *
 * Proporcional parece lo justo y no lo es: son dos tarjetas arriba contra una
 * cola que puede tener veinte, y el reparto por contenido dejaría el grupo de
 * arriba en un renglón y medio. En porcentajes del cuerpo, el reparto es el
 * mismo con cinco pendientes que con cincuenta, y como las dos bases suman 100
 * nunca queda hueco que repartir ni sobra alto que empuje el widget fuera de la
 * pantalla.
 */
.revision--desplegada .grupo--primeras {
  flex-basis: 40%;
}

.revision--desplegada .grupo--restantes {
  flex-basis: 60%;
}

.grupo--primeras {
  overflow-y: auto;
}

/* El filete separa los dos desplazamientos. Sin él, la tarjeta que el grupo de
   arriba corta por la mitad parece la primera de la lista de abajo. */
.revision--desplegada .grupo--restantes {
  padding-top: var(--blubathon-esp-14);
  border-top: 1px solid var(--blubathon-ia-linea);
}

.grupo__titulo {
  font-size: var(--blubathon-fs-11);
  font-weight: 700;
  letter-spacing: var(--blubathon-track-014);
  text-transform: uppercase;
  color: var(--blubathon-ia-texto-suave);
}

/* El desplazamiento del grupo de abajo va en la lista y no en la sección, para
   que su rótulo se quede quieto mientras las tarjetas pasan. */
.grupo__lista {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: var(--blubathon-esp-12);
  min-block-size: 0;
  overflow-y: auto;
}

/* Sitio para el anillo de foco de la tarjeta que se desplaza dentro del grupo:
   sin él, el borde queda cortado contra el borde del contenedor. */
.grupo--primeras,
.grupo__lista {
  padding-right: var(--blubathon-esp-6);
  overscroll-behavior: contain;
}

.revision__ver {
  display: inline-flex;
  gap: var(--blubathon-esp-6);
  align-self: center;
  align-items: center;
  min-height: var(--blubathon-toque);
  padding-inline: var(--blubathon-esp-12);
  font-size: var(--blubathon-fs-135);
  font-weight: 700;
  color: var(--blubathon-marca-accion);
}

.revision__ver:hover {
  text-decoration: underline;
}

.revision__ver:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-marca-accion);
  outline-offset: var(--blubathon-foco-offset);
  border-radius: var(--blubathon-radio-10);
}

.revision__chevron {
  width: var(--blubathon-icono-14);
  height: var(--blubathon-icono-14);
}

.revision__chevron--abajo {
  transform: rotate(90deg);
}

.revision__chevron--arriba {
  transform: rotate(-90deg);
}
</style>
