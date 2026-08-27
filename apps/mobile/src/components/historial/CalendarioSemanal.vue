<script setup lang="ts">
import type { CeldaCalendario } from "@/dominio/dia";

defineProps<{
  celdas: readonly CeldaCalendario[];
  /** ISO del día abierto en el detalle. */
  seleccionado: string;
}>();

defineEmits<{ seleccionar: [iso: string] }>();

const ESTADO_EN_PALABRAS: Record<string, string> = {
  respondido: "cuestionario respondido",
  "sin-responder": "sin cuestionario",
  futuro: "todavía no ha llegado",
};

/**
 * El nombre accesible dice todo lo que la celda muestra con color y con forma:
 * qué día es, si tiene cuestionario y cuántas variables críticas trae.
 */
function etiquetaCelda(celda: CeldaCalendario): string {
  const partes = [
    `${celda.dia.nombre} ${celda.dia.numero}`,
    ESTADO_EN_PALABRAS[celda.resumen.estado] ?? "",
  ];
  if (celda.dia.esHoy) partes.push("hoy");
  const criticas = celda.resumen.criticas.length;
  if (criticas > 0) {
    partes.push(criticas === 1 ? "1 variable crítica" : `${criticas} variables críticas`);
  }
  return partes.filter((parte) => parte !== "").join(", ");
}
</script>

<template>
  <ul class="calendario">
    <li v-for="celda in celdas" :key="celda.dia.iso" class="calendario__hueco">
      <button
        type="button"
        class="dia"
        :class="[
          `dia--${celda.resumen.estado}`,
          {
            'dia--hoy': celda.dia.esHoy,
            'dia--elegido': celda.dia.iso === seleccionado,
          },
        ]"
        :disabled="celda.dia.esFuturo"
        :aria-pressed="celda.dia.iso === seleccionado"
        :aria-label="etiquetaCelda(celda)"
        @click="$emit('seleccionar', celda.dia.iso)"
      >
        <span class="dia__inicial" aria-hidden="true">{{ celda.dia.inicial }}</span>
        <span class="dia__numero" aria-hidden="true">{{ celda.dia.numero }}</span>

        <span class="dia__senales" aria-hidden="true">
          <span class="dia__punto"></span>
          <span v-if="celda.resumen.criticas.length > 0" class="dia__critica"></span>
        </span>
      </button>
    </li>
  </ul>
</template>

<style scoped>
/*
 * Siete columnas iguales. En el ancho más estrecho que soporta la aplicación
 * —320px— la celda sigue entrando, porque el acolchado lateral de la tarjeta se
 * queda en 6: el calendario es la única pieza que necesita todo el ancho, y
 * pagarlo con margen sería quedarse sin días.
 */
.calendario {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: var(--blubathon-esp-4);
}

.calendario__hueco {
  min-width: 0;
}

/*
 * La celda dice tres cosas a la vez y ninguna depende solo del color: el estado
 * lo lleva el punto, el día de hoy lo lleva el anillo, y el seleccionado lo
 * lleva el relleno. El nombre accesible las dice todas escritas.
 */
.dia {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--blubathon-esp-4);
  width: 100%;
  min-height: var(--blubathon-celda-alto);
  padding-block: var(--blubathon-esp-8);
  background: var(--blubathon-superficie);
  border: 1px solid var(--blubathon-linea);
  border-radius: var(--blubathon-radio-14);
}

.dia:hover:not(:disabled) {
  border-color: var(--blubathon-punto-activo);
}

.dia:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-foco-oscuro);
  outline-offset: var(--blubathon-foco-offset);
}

.dia:disabled {
  cursor: default;
  opacity: 0.55;
}

.dia__inicial {
  font-size: var(--blubathon-fs-11);
  font-weight: 700;
  letter-spacing: var(--blubathon-track-012);
  text-transform: uppercase;
  color: var(--blubathon-gris-texto);
}

.dia__numero {
  font-size: var(--blubathon-fs-155);
  font-weight: 700;
  color: var(--blubathon-marca-titulo);
}

.dia__senales {
  display: flex;
  align-items: center;
  gap: 3px;
  height: var(--blubathon-punto);
}

.dia__punto {
  width: var(--blubathon-punto);
  height: var(--blubathon-punto);
  background: var(--blubathon-punto-inactivo);
  border-radius: 50%;
}

.dia--respondido .dia__punto {
  background: var(--blubathon-punto-activo);
}

/* Un día futuro no tiene estado que mostrar: la celda se queda sin punto. */
.dia--futuro .dia__punto {
  background: none;
}

/* La variable crítica es un cuadrado girado, no otro círculo: dos puntos del
   mismo tamaño se leen como una sola señal partida en dos. */
.dia__critica {
  width: 7px;
  height: 7px;
  background: var(--blubathon-critica-media-texto);
  border-radius: 1px;
  transform: rotate(45deg);
}

.dia--hoy {
  border-color: var(--blubathon-marca-accion);
}

.dia--elegido {
  background: var(--blubathon-marca-icono-fondo);
  border-color: var(--blubathon-marca-accion);
  border-width: 2px;
}

.dia--elegido .dia__numero {
  color: var(--blubathon-marca-profundo);
}

@media (min-width: 900px) {
  .calendario {
    gap: var(--blubathon-esp-8);
  }

  .dia {
    min-height: var(--blubathon-celda-alto-amplio);
    gap: var(--blubathon-esp-6);
  }

  .dia__numero {
    font-size: var(--blubathon-fs-20);
  }
}
</style>
