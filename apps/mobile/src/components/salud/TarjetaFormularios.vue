<script setup lang="ts">
import IconoChevron from "@/components/icons/IconoChevron.vue";
import { ETIQUETA_ESTADO_FORMULARIO, type RegistroFormulario } from "@/types/salud";

defineProps<{
  registros: readonly RegistroFormulario[];
}>();

defineEmits<{
  verMas: [];
  abrirRegistro: [id: string];
}>();

function etiquetaFila(registro: RegistroFormulario): string {
  return `Abrir el formulario de ${registro.dia}, ${ETIQUETA_ESTADO_FORMULARIO[registro.estado].toLowerCase()}`;
}
</script>

<template>
  <section class="formularios">
    <div class="formularios__cabecera">
      <h2 class="formularios__titulo">Últimos formularios</h2>
      <button
        type="button"
        class="formularios__accion"
        aria-label="Ver todos los formularios"
        @click="$emit('verMas')"
      >
        ver más
      </button>
    </div>

    <ul class="formularios__lista">
      <li v-for="registro in registros" :key="registro.id" class="formulario">
        <!-- Cada día es un destino, así que cada día es un botón: la fila
             entera se pulsa y el galón dice hacia dónde lleva. -->
        <button
          type="button"
          class="formulario__fila"
          :aria-label="etiquetaFila(registro)"
          @click="$emit('abrirRegistro', registro.id)"
        >
          <span class="formulario__punto" :class="`formulario__punto--${registro.estado}`"></span>
          <span class="formulario__dia">{{ registro.dia }}</span>
          <!-- El punto nunca va solo: el estado también se lee. -->
          <span class="formulario__estado">{{ ETIQUETA_ESTADO_FORMULARIO[registro.estado] }}</span>
          <IconoChevron class="formulario__chevron" />
        </button>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.formularios {
  padding: var(--faro-esp-18) var(--faro-esp-16);
  background: var(--faro-superficie);
  border-radius: var(--faro-radio-24);
  box-shadow: var(--faro-sombra-tarjeta);
}

.formularios__cabecera {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--faro-esp-12);
}

.formularios__titulo {
  font-size: var(--faro-fs-15);
  font-weight: 700;
  color: var(--faro-verde-profundo);
}

.formularios__accion {
  /* 44x44 de área táctil sin alterar la línea base ni el alto de la cabecera:
     el padding crece y el margen negativo lo devuelve. */
  min-width: var(--faro-toque);
  min-height: var(--faro-toque);
  padding: var(--faro-esp-14) var(--faro-esp-10);
  margin: calc(var(--faro-esp-14) * -1) calc(var(--faro-esp-10) * -1);
  font-size: var(--faro-fs-13);
  font-weight: 700;
  color: var(--faro-verde-accion);
  border-radius: var(--faro-radio-10);
}

.formularios__accion:focus-visible {
  outline: var(--faro-foco-grosor) solid var(--faro-foco-oscuro);
  outline-offset: var(--faro-foco-offset);
}

.formularios__lista {
  margin-top: var(--faro-esp-6);
}

.formulario + .formulario {
  border-top: 1px solid var(--faro-linea);
}

/*
 * La fila entera es el área pulsable: 44 de alto y todo el ancho de la tarjeta.
 * Los márgenes negativos la estiran hasta el acolchado de la tarjeta para que
 * el realce al pulsar llegue de borde a borde, sin mover el texto de sitio.
 */
.formulario__fila {
  display: flex;
  align-items: center;
  gap: var(--faro-esp-12);
  width: calc(100% + var(--faro-esp-16));
  min-height: var(--faro-toque);
  padding-inline: var(--faro-esp-8);
  margin-inline: calc(var(--faro-esp-8) * -1);
  text-align: left;
  border-radius: var(--faro-radio-10);
}

.formulario__fila:hover,
.formulario__fila:active {
  background: var(--faro-fila-activa);
}

.formulario__fila:focus-visible {
  outline: var(--faro-foco-grosor) solid var(--faro-foco-oscuro);
  outline-offset: calc(var(--faro-foco-offset) * -1);
}

.formulario__punto {
  flex: none;
  width: var(--faro-punto);
  height: var(--faro-punto);
  border-radius: 50%;
}

.formulario__punto--respondido {
  background: var(--faro-punto-activo);
}

.formulario__punto--sin-responder {
  background: var(--faro-punto-inactivo);
}

.formulario__dia {
  flex: 1;
  min-width: 0;
  font-size: var(--faro-fs-135);
  font-weight: 700;
  color: var(--faro-verde-texto);
}

.formulario__estado {
  flex: none;
  font-size: var(--faro-fs-125);
  color: var(--faro-gris-texto);
}

.formulario__chevron {
  flex: none;
  width: var(--faro-icono-14);
  height: var(--faro-icono-14);
  color: var(--faro-gris-texto);
}
</style>
