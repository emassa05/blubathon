<script setup lang="ts">
import { ETIQUETA_ESTADO_FORMULARIO, type RegistroFormulario } from "@/types/salud";

defineProps<{
  registros: readonly RegistroFormulario[];
}>();

defineEmits<{
  verMas: [];
}>();
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
        <span class="formulario__punto" :class="`formulario__punto--${registro.estado}`"></span>
        <span class="formulario__dia">{{ registro.dia }}</span>
        <!-- El punto nunca va solo: el estado también se lee. -->
        <span class="formulario__estado">{{ ETIQUETA_ESTADO_FORMULARIO[registro.estado] }}</span>
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
  font-weight: 600;
  color: var(--faro-verde-accion);
  border-radius: var(--faro-radio-10);
}

.formularios__accion:focus-visible {
  outline: var(--faro-foco-grosor) solid var(--faro-foco-oscuro);
  outline-offset: var(--faro-foco-offset);
}

.formularios__lista {
  display: flex;
  flex-direction: column;
  gap: var(--faro-esp-12);
  margin-top: var(--faro-esp-12);
}

.formulario {
  display: flex;
  align-items: center;
  gap: var(--faro-esp-12);
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
  font-weight: 600;
  color: var(--faro-verde-texto);
}

.formulario__estado {
  flex: none;
  font-size: var(--faro-fs-125);
  color: var(--faro-gris-texto);
}
</style>
