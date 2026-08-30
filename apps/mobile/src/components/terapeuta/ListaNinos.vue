<script setup lang="ts">
import AvatarNino from "@/components/base/AvatarNino.vue";
import { CLASE_BANDA, bandaRiesgo } from "@/theme/riesgo";
import type { FichaNino } from "@/types/terapeuta";

defineProps<{
  fichas: readonly FichaNino[];
  seleccionado: string | null;
  cargando: boolean;
}>();

const emitir = defineEmits<{ seleccionar: [id: string] }>();

/** El riesgo escrito, o la abstención dicha con palabras.
 *
 * "—" o un guion no valen: en una columna de cifras, un hueco se lee como un
 * cero pequeño. Sin estimación hay que decirlo. */
function cifra(riesgo: number | null): string {
  return riesgo === null ? "s/d" : `${Math.round(riesgo)}%`;
}

function descripcion(ficha: FichaNino): string {
  const riesgo =
    ficha.riesgo === null
      ? "sin estimación de riesgo"
      : `riesgo ${Math.round(ficha.riesgo)} por ciento`;
  return `${ficha.etiqueta}, ${riesgo}`;
}
</script>

<template>
  <section class="lista" aria-labelledby="lista-ninos-titulo">
    <h2 id="lista-ninos-titulo" class="lista__titulo">Niños en seguimiento</h2>

    <p v-if="cargando" class="lista__aviso" role="status">Cargando la cartera…</p>

    <p v-else-if="fichas.length === 0" class="lista__aviso">
      No hay niños asignados en esta organización.
    </p>

    <!--
      Una lista de botones y no una lista de enlaces: no se navega a ninguna
      parte, se cambia lo que muestran los otros dos widgets. `aria-current`
      dice cuál está activo, que es lo que un lector necesita para no perder
      dónde está al recorrer la columna.
    -->
    <ul v-else class="lista__filas">
      <li v-for="ficha in fichas" :key="ficha.id">
        <button
          type="button"
          class="fila"
          :class="[
            CLASE_BANDA[bandaRiesgo(ficha.riesgo)],
            { 'fila--activa': ficha.id === seleccionado },
          ]"
          :aria-current="ficha.id === seleccionado ? 'true' : undefined"
          :aria-label="descripcion(ficha)"
          @click="emitir('seleccionar', ficha.id)"
        >
          <AvatarNino class="fila__avatar" :etiqueta="ficha.etiqueta" :semilla="ficha.id" />

          <span class="fila__cuerpo">
            <span class="fila__nombre">{{ ficha.etiqueta }}</span>
            <span class="fila__detalle">
              {{ ficha.serie.length }} {{ ficha.serie.length === 1 ? "día" : "días" }} registrados
            </span>
          </span>

          <span class="fila__riesgo" aria-hidden="true">{{ cifra(ficha.riesgo) }}</span>
        </button>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.lista {
  display: flex;
  flex-direction: column;
  min-block-size: 0;
  padding: var(--blubathon-esp-16);
  background: var(--blubathon-superficie);
  border-radius: var(--blubathon-radio-24);
  box-shadow: var(--blubathon-elev-1);
}

.lista__titulo {
  font-size: var(--blubathon-fs-11);
  font-weight: 700;
  letter-spacing: var(--blubathon-track-014);
  text-transform: uppercase;
  color: var(--blubathon-gris-texto);
}

.lista__aviso {
  margin-top: var(--blubathon-esp-16);
  font-size: var(--blubathon-fs-135);
  color: var(--blubathon-gris-texto);
}

/*
 * Aire entre filas y no un filete: cada niño es una pieza que se elige entera,
 * y con la separación el bloque que se ilumina al pasar por encima coincide con
 * lo que se va a pulsar. Un filete además chocaría con las esquinas redondas.
 *
 * El desplazamiento vive aquí y no en la página: la tarjeta llega hasta el
 * borde de la ventana, así que con veinte niños lo que se mueve es la lista y
 * el rótulo se queda donde estaba. En móvil la tarjeta no tiene altura fija, no
 * sobra nada y este `auto` no llega a desplazar nunca.
 */
.lista__filas {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: var(--blubathon-esp-6);
  min-block-size: 0;
  margin-top: var(--blubathon-esp-12);
  /* Sitio para el anillo de foco de la fila que se desplaza: pegado al borde
     del contenedor quedaría cortado por la mitad. */
  padding-right: var(--blubathon-esp-4);
  overflow-y: auto;
  list-style: none;
  overscroll-behavior: contain;
}

.fila {
  display: flex;
  gap: var(--blubathon-esp-12);
  align-items: center;
  width: 100%;
  min-height: var(--blubathon-toque);
  padding: var(--blubathon-esp-10);
  font: inherit;
  text-align: left;
  cursor: pointer;
  background: none;
  border: 0;
  border-radius: var(--blubathon-radio-14);
}

.fila:hover {
  background: var(--blubathon-fila-activa);
}

.fila:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-marca-accion);
  outline-offset: calc(var(--blubathon-foco-offset) * -1);
}

.fila--activa {
  background: var(--blubathon-fila-activa);
}

/* El disco de la inicial es identidad y no estado: el mismo tono aquí y en la
   cola de revisión, para reconocer al niño saltando de una columna a otra. */
.fila__avatar {
  align-self: center;
}

.fila__cuerpo {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  gap: 2px;
}

.fila__nombre {
  overflow: hidden;
  font-size: var(--blubathon-fs-15);
  font-weight: 700;
  color: var(--blubathon-marca-titulo);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.fila__detalle {
  font-size: var(--blubathon-fs-12);
  color: var(--blubathon-gris-texto);
}

/*
 * La cifra lleva el color de la banda, que la fila hereda de su clase. Es lo
 * único de la fila que lo lleva: la fila entera teñida convertiría la columna
 * en un semáforo de seis luces donde ninguna destaca.
 *
 * El color nunca va solo, y aquí menos que en ningún sitio: el dato es el
 * número, así que quien no distingue los tonos no pierde nada.
 */
.fila__riesgo {
  flex: none;
  min-width: 3ch;
  font-size: var(--blubathon-fs-135);
  font-weight: 700;
  color: var(--blubathon-texto-fuerte, var(--blubathon-marca-texto));
  text-align: right;
  font-variant-numeric: tabular-nums;
}
</style>
