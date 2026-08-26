<script setup lang="ts">
import { computed } from "vue";

import { FARO_TEXTS_ES } from "@/api/contrato";
import ListaCriticas from "@/components/cuestionario/ListaCriticas.vue";
import IconoPortapapeles from "@/components/icons/IconoPortapapeles.vue";
import { bandaDelDia, type ResumenDia } from "@/dominio/dia";
import { etiquetaDiaLargo } from "@/dominio/semana";
import { CLASE_BANDA } from "@/theme/riesgo";

const props = defineProps<{ resumen: ResumenDia }>();

defineEmits<{ abrirCuestionario: [] }>();

const titulo = computed(() => etiquetaDiaLargo(props.resumen.fecha));

const ESTADO_EN_PALABRAS: Record<ResumenDia["estado"], string> = {
  respondido: "Respondido",
  "sin-responder": "Sin responder",
  futuro: "Todavía no llega",
};

/**
 * La cifra del día, solo cuando existe.
 *
 * El track personal se abstiene mientras no tenga cinco resultados verificados
 * (SPEC 8.5 / C19), y hasta entonces no hay número que dar. Antes se dibujaba
 * igualmente una caja con un guion bajo el rótulo "Riesgo", que se leía como
 * una cifra que no se actualizaba nunca. Ahora la caja no se dibuja y el porqué
 * lo dice la nota.
 */
const cifra = computed(() =>
  props.resumen.probabilidad === null ? null : `${Math.round(props.resumen.probabilidad * 100)}%`,
);

const notaEstimacion = computed(() => {
  if (props.resumen.probabilidad !== null) return "";
  if (props.resumen.estado !== "respondido") return "";
  return props.resumen.estimacionAbstenida
    ? "El modelo se abstuvo: todavía no hay suficiente historial verificado."
    : "Este día no tiene estimación numérica.";
});

const banda = computed(() => bandaDelDia(props.resumen));

const RECOMENDACION_EN_PALABRAS: Record<string, string> = {
  matched: "Hay una recomendación guardada para este día.",
  pending: "La recomendación de este día se está preparando.",
  abstained: "Este día no recibió recomendación.",
};

const recomendacion = computed(() => {
  const estado = props.resumen.recomendacion?.status;
  return estado === undefined ? null : (RECOMENDACION_EN_PALABRAS[estado] ?? null);
});

const resultado = computed(() => {
  const estado = props.resumen.resultado?.status;
  if (estado === undefined) return null;
  const etiquetas = FARO_TEXTS_ES.outcomeResolutionLabelsEs as Readonly<Record<string, string>>;
  return etiquetas[estado] ?? null;
});

const accion = computed(() =>
  props.resumen.estado === "respondido" ? "Ver y completar respuestas" : "Responder cuestionario",
);
</script>

<template>
  <section class="detalle">
    <header class="detalle__cabecera">
      <div class="detalle__rotulos">
        <h2 class="detalle__titulo">{{ titulo }}</h2>
        <p class="detalle__estado" :class="`detalle__estado--${resumen.estado}`">
          {{ ESTADO_EN_PALABRAS[resumen.estado] }}
        </p>
      </div>

      <!-- La cifra solo aparece si existe. La banda pinta el fondo únicamente
           cuando hay número que encuadrar. -->
      <p v-if="cifra" class="detalle__estimacion" :class="banda ? CLASE_BANDA[banda] : ''">
        <span class="detalle__cifra">{{ cifra }}</span>
        <span class="detalle__pie">Riesgo</span>
      </p>
    </header>

    <p v-if="notaEstimacion" class="detalle__nota">{{ notaEstimacion }}</p>

    <ul v-if="recomendacion || resultado" class="detalle__hechos">
      <li v-if="recomendacion" class="detalle__hecho">{{ recomendacion }}</li>
      <li v-if="resultado" class="detalle__hecho">Resultado del día: {{ resultado }}</li>
    </ul>

    <p v-if="resumen.soloLocal" class="detalle__nota">
      Este envío está guardado en este dispositivo y la API todavía no lo devuelve en el historial.
    </p>

    <ListaCriticas
      v-if="resumen.criticas.length > 0"
      class="detalle__criticas"
      :criticas="resumen.criticas"
    />

    <p v-else-if="resumen.estado === 'respondido'" class="detalle__nota">
      Ninguna respuesta de este día se sale de lo habitual.
    </p>

    <p v-else-if="resumen.estado === 'sin-responder'" class="detalle__nota">
      {{ FARO_TEXTS_ES.emptyEs }} Responder el cuestionario de este día es lo que abre su
      estimación.
    </p>

    <button
      v-if="resumen.estado !== 'futuro'"
      type="button"
      class="detalle__accion"
      @click="$emit('abrirCuestionario')"
    >
      <span class="detalle__insignia" aria-hidden="true">
        <IconoPortapapeles class="detalle__icono" />
      </span>
      {{ accion }}
    </button>
  </section>
</template>

<style scoped>
.detalle {
  padding: var(--faro-esp-16);
  background: var(--faro-superficie);
  border-radius: var(--faro-radio-24);
  box-shadow: var(--faro-elev-1);
}

.detalle__cabecera {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--faro-esp-12);
}

.detalle__rotulos {
  min-width: 0;
}

.detalle__titulo {
  font-size: var(--faro-fs-17);
  font-weight: 700;
  color: var(--faro-verde-profundo);
}

.detalle__estado {
  display: inline-block;
  margin-top: var(--faro-esp-6);
  padding: var(--faro-esp-4) var(--faro-esp-9);
  font-size: var(--faro-fs-11);
  font-weight: 700;
  letter-spacing: var(--faro-track-012);
  text-transform: uppercase;
  color: var(--faro-gris-texto);
  background: var(--faro-fila-activa);
  border-radius: var(--faro-radio-pastilla);
}

.detalle__estado--respondido {
  color: var(--faro-verde-accion);
  background: var(--faro-verde-icono-fondo);
}

/*
 * La cifra del día usa la paleta de su banda, la misma del panel de Salud: si un
 * día es "medio", es del mismo amarillo aquí y allá. Sin número no hay banda, y
 * entonces la caja se queda neutra.
 */
.detalle__estimacion {
  display: flex;
  flex: none;
  flex-direction: column;
  align-items: center;
  padding: var(--faro-esp-8) var(--faro-esp-12);
  background: var(--faro-panel, var(--faro-fila-activa));
  border-radius: var(--faro-radio-14);
}

.detalle__cifra {
  font-size: var(--faro-fs-20);
  font-weight: 700;
  color: var(--faro-texto-fuerte, var(--faro-verde-titulo));
}

.detalle__pie {
  font-size: var(--faro-fs-11);
  font-weight: 700;
  letter-spacing: var(--faro-track-012);
  text-transform: uppercase;
  color: var(--faro-texto-suave, var(--faro-gris-texto));
}

.detalle__nota {
  margin-top: var(--faro-esp-12);
  font-size: var(--faro-fs-125);
  line-height: 1.45;
  color: var(--faro-gris-texto);
}

.detalle__hechos {
  margin-top: var(--faro-esp-12);
}

.detalle__hecho {
  padding-block: var(--faro-esp-6);
  font-size: var(--faro-fs-125);
  color: var(--faro-verde-texto);
}

.detalle__hecho + .detalle__hecho {
  border-top: 1px solid var(--faro-linea);
}

/* La lista de críticas ya es una tarjeta: dentro de esta se queda sin sombra
   para no dibujar una caja dentro de otra. */
.detalle__criticas {
  margin-top: var(--faro-esp-14);
  padding: 0;
  box-shadow: none;
}

.detalle__accion {
  display: flex;
  align-items: center;
  gap: var(--faro-esp-12);
  width: 100%;
  min-height: var(--faro-toque);
  margin-top: var(--faro-esp-16);
  padding: var(--faro-esp-8) var(--faro-esp-12);
  font-size: var(--faro-fs-135);
  font-weight: 700;
  text-align: left;
  color: var(--faro-aviso-titulo);
  background: var(--faro-aviso-fondo);
  border-radius: var(--faro-radio-18);
}

.detalle__accion:focus-visible {
  outline: var(--faro-foco-grosor) solid var(--faro-aviso-titulo);
  outline-offset: var(--faro-foco-offset);
}

.detalle__insignia {
  display: grid;
  flex: none;
  place-items: center;
  width: var(--faro-caja-icono);
  height: var(--faro-caja-icono);
  color: var(--faro-superficie);
  background: var(--faro-aviso-insignia);
  border-radius: var(--faro-radio-10);
}

.detalle__icono {
  width: var(--faro-icono-16);
  height: var(--faro-icono-16);
}
</style>
