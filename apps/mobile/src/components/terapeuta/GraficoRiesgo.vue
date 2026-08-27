<script setup lang="ts">
import { computed } from "vue";

import { CORTE_ALTO, CORTE_MEDIO } from "@/theme/riesgo";
import type { PuntoRiesgo } from "@/types/terapeuta";

const props = defineProps<{
  serie: readonly PuntoRiesgo[];
  /** Etiqueta del niño, para el resumen que oye un lector de pantalla. */
  etiqueta: string;
}>();

/*
 * Lienzo en coordenadas propias, con `viewBox`: el SVG escala solo al ancho que
 * le dé la tarjeta y no hay que medir nada en tiempo de ejecución. Los números
 * de aquí son unidades del dibujo, no píxeles.
 */
const ANCHO = 320;
const ALTO = 120;
const MARGEN = { arriba: 8, derecha: 4, abajo: 16, izquierda: 4 };

const TRAZO = ANCHO - MARGEN.izquierda - MARGEN.derecha;
const CAJA = ALTO - MARGEN.arriba - MARGEN.abajo;

/** La escala vertical es 0-100 fija y no se ajusta a los datos.
 *
 * Un eje que se autoescala hace que una serie plana entre 12 % y 14 % se dibuje
 * como una montaña rusa, y el terapeuta que compara dos niños compararía dos
 * escalas distintas. Con 0-100 fijo, la altura significa lo mismo siempre. */
function y(valor: number): number {
  return MARGEN.arriba + CAJA * (1 - Math.min(100, Math.max(0, valor)) / 100);
}

function x(indice: number): number {
  if (props.serie.length <= 1) return MARGEN.izquierda + TRAZO / 2;
  return MARGEN.izquierda + (TRAZO * indice) / (props.serie.length - 1);
}

interface PuntoDibujado {
  readonly indice: number;
  readonly punto: PuntoRiesgo;
  readonly cx: number;
  readonly cy: number;
}

const estimados = computed<PuntoDibujado[]>(() =>
  props.serie
    .map((punto, indice) => ({ indice, punto, cx: x(indice), cy: y(punto.riesgo ?? 0) }))
    .filter((dibujado) => dibujado.punto.riesgo !== null),
);

/**
 * La línea, partida en tramos.
 *
 * Un `polyline` único uniría los dos lados de una abstención con un segmento
 * recto, y ese segmento afirmaría una progresión que el modelo no estimó. Aquí
 * cada racha de días consecutivos con cifra es su propio trazo, y el hueco se
 * ve como lo que es: un hueco.
 */
const tramos = computed<string[]>(() => {
  const salida: string[] = [];
  let actual: string[] = [];

  props.serie.forEach((punto, indice) => {
    if (punto.riesgo === null) {
      if (actual.length > 1) salida.push(actual.join(" "));
      actual = [];
      return;
    }
    actual.push(`${x(indice).toFixed(1)},${y(punto.riesgo).toFixed(1)}`);
  });
  if (actual.length > 1) salida.push(actual.join(" "));
  return salida;
});

/** Puntos sueltos: un día con cifra entre dos abstenciones no forma tramo y sin
 *  esto no se dibujaría nada, pese a haber estimación ese día. */
const sueltos = computed<PuntoDibujado[]>(() =>
  estimados.value.filter((dibujado) => {
    const antes = props.serie[dibujado.indice - 1]?.riesgo ?? null;
    const despues = props.serie[dibujado.indice + 1]?.riesgo ?? null;
    return antes === null && despues === null;
  }),
);

/**
 * La banda del intervalo, como un área cerrada.
 *
 * Solo se dibuja sobre tramos continuos, por lo mismo que la línea: un área que
 * cruza una abstención rellenaría de color un día del que no se sabe nada.
 */
const areas = computed<string[]>(() => {
  const salida: string[] = [];
  let arriba: string[] = [];
  let abajo: string[] = [];

  const cerrar = (): void => {
    if (arriba.length > 1) salida.push(`${arriba.join(" ")} ${abajo.reverse().join(" ")}`);
    arriba = [];
    abajo = [];
  };

  props.serie.forEach((punto, indice) => {
    if (punto.banda === null) {
      cerrar();
      return;
    }
    const columna = x(indice).toFixed(1);
    arriba.push(`${columna},${y(punto.banda[1]).toFixed(1)}`);
    abajo.push(`${columna},${y(punto.banda[0]).toFixed(1)}`);
  });
  cerrar();
  return salida;
});

/** Los días con resultado confirmado. Es lo que pasó, no lo que se estimó, así
 *  que se marca en la base y no sobre la línea: son dos afirmaciones distintas. */
const confirmados = computed(() =>
  props.serie
    .map((punto, indice) => ({ punto, cx: x(indice) }))
    .filter((marca) => marca.punto.resultado !== null),
);

const hayEstimacion = computed(() => estimados.value.length > 0);

/**
 * El texto que oye quien no ve el dibujo.
 *
 * No es "gráfico de riesgo": es lo que el gráfico permite concluir. Un lector de
 * pantalla que anuncia el nombre del componente no ha transmitido nada.
 */
const resumen = computed(() => {
  if (props.serie.length === 0) return `${props.etiqueta}: todavía no hay días registrados.`;
  if (!hayEstimacion.value) {
    return `${props.etiqueta}: ${props.serie.length} días registrados, sin estimación de riesgo en ninguno.`;
  }
  const cifras = estimados.value.map((dibujado) => dibujado.punto.riesgo ?? 0);
  const ultimo = cifras[cifras.length - 1] ?? 0;
  const episodios = props.serie.filter((punto) => punto.resultado === "ocurrio").length;
  return (
    `${props.etiqueta}: riesgo estimado en ${cifras.length} de ${props.serie.length} días, ` +
    `entre ${Math.min(...cifras)} y ${Math.max(...cifras)} por ciento, ` +
    `último ${ultimo} por ciento. ${episodios} episodios confirmados en el periodo.`
  );
});
</script>

<template>
  <figure class="grafico">
    <svg
      class="grafico__lienzo"
      :viewBox="`0 0 ${ANCHO} ${ALTO}`"
      role="img"
      :aria-label="resumen"
      preserveAspectRatio="none"
    >
      <!-- Los cortes de banda, de fondo. Son la referencia contra la que se lee
           la altura: sin ellos, "40" es un punto a media altura y nada más. -->
      <line
        class="grafico__corte"
        :x1="MARGEN.izquierda"
        :x2="ANCHO - MARGEN.derecha"
        :y1="y(CORTE_ALTO)"
        :y2="y(CORTE_ALTO)"
      />
      <line
        class="grafico__corte grafico__corte--medio"
        :x1="MARGEN.izquierda"
        :x2="ANCHO - MARGEN.derecha"
        :y1="y(CORTE_MEDIO)"
        :y2="y(CORTE_MEDIO)"
      />

      <polygon
        v-for="(area, indice) in areas"
        :key="`a${indice}`"
        class="grafico__banda"
        :points="area"
      />

      <polyline
        v-for="(tramo, indice) in tramos"
        :key="`t${indice}`"
        class="grafico__linea"
        :points="tramo"
      />

      <circle
        v-for="dibujado in sueltos"
        :key="`s${dibujado.indice}`"
        class="grafico__suelto"
        :cx="dibujado.cx"
        :cy="dibujado.cy"
        r="2.2"
      />

      <!-- Los resultados confirmados, en la base. Un episodio es un hecho
           reportado; la línea de arriba es una estimación. Superponerlos haría
           que se leyeran como la misma clase de cosa. -->
      <rect
        v-for="(marca, indice) in confirmados"
        :key="`c${indice}`"
        class="grafico__marca"
        :class="{ 'grafico__marca--episodio': marca.punto.resultado === 'ocurrio' }"
        :x="marca.cx - 1.5"
        :y="ALTO - MARGEN.abajo + 5"
        width="3"
        height="6"
        rx="1.5"
      />
    </svg>

    <figcaption class="grafico__pie">
      <span class="grafico__leyenda">
        <span class="grafico__muestra grafico__muestra--episodio" aria-hidden="true"></span>
        Episodio confirmado
      </span>
      <span class="grafico__leyenda">
        <span class="grafico__muestra" aria-hidden="true"></span>
        Sin episodio
      </span>
      <!-- Se dice que hay huecos en vez de disimularlos. Es la abstención del
           modelo, que es una propiedad del producto y no una falla del dibujo. -->
      <span v-if="!hayEstimacion" class="grafico__aviso">Sin estimación en el periodo</span>
    </figcaption>
  </figure>
</template>

<style scoped>
.grafico {
  margin: 0;
}

/*
 * `preserveAspectRatio="none"` y alto fijo: el gráfico se estira a lo ancho de
 * la tarjeta y conserva su altura. La proporción no significa nada aquí —el eje
 * vertical es 0-100 fijo y el horizontal son días—, y dejarla libre evita que
 * en una ventana ancha la tarjeta crezca hasta media pantalla.
 */
.grafico__lienzo {
  display: block;
  width: 100%;
  height: var(--blubathon-grafico-alto);
  overflow: visible;
}

.grafico__corte {
  stroke: var(--blubathon-linea);
  stroke-width: 1;
  stroke-dasharray: 3 3;
}

.grafico__corte--medio {
  opacity: 0.6;
}

/* El intervalo, no la cifra. Muy tenue a propósito: es la incertidumbre, y si
   pesara más que la línea se leería como el dato. */
.grafico__banda {
  fill: var(--blubathon-marca-icono-fondo);
  opacity: 0.75;
}

.grafico__linea {
  fill: none;
  stroke: var(--blubathon-marca-accion);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.grafico__suelto {
  fill: var(--blubathon-marca-accion);
}

.grafico__marca {
  fill: var(--blubathon-punto-inactivo);
}

.grafico__marca--episodio {
  fill: var(--blubathon-aviso-insignia);
}

.grafico__pie {
  display: flex;
  flex-wrap: wrap;
  gap: var(--blubathon-esp-12);
  margin-top: var(--blubathon-esp-10);
  font-size: var(--blubathon-fs-11);
  color: var(--blubathon-gris-texto);
}

.grafico__leyenda {
  display: inline-flex;
  align-items: center;
  gap: var(--blubathon-esp-6);
}

.grafico__muestra {
  width: var(--blubathon-esp-6);
  height: var(--blubathon-esp-10);
  background: var(--blubathon-punto-inactivo);
  border-radius: var(--blubathon-radio-pastilla);
}

.grafico__muestra--episodio {
  background: var(--blubathon-aviso-insignia);
}

.grafico__aviso {
  margin-left: auto;
  color: var(--blubathon-marca-texto);
}
</style>
