<script setup lang="ts">
import IconoDestello from "@/components/icons/IconoDestello.vue";
import type { Recomendacion } from "@/types/salud";

defineProps<{
  recomendacion: Recomendacion;
}>();

const SOBRETITULO = "Recomendación de hoy";
</script>

<template>
  <section class="recomendacion">
    <h2 class="recomendacion__marca">
      <span class="recomendacion__insignia" aria-hidden="true">
        <IconoDestello class="recomendacion__destello" />
      </span>
      <span>{{ SOBRETITULO }}</span>
    </h2>

    <p class="recomendacion__frase">{{ recomendacion.texto }}</p>
  </section>
</template>

<style scoped>
/*
 * Es una tarjeta del mismo sistema que las otras dos: superficie blanca, mismo
 * radio, misma elevación. Antes era un bloque de color justo debajo de un panel
 * de color, y se leía como un trozo del panel que se hubiera caído.
 *
 * Lo que la distingue es el acento, no la superficie: un lavado del tono de la
 * banda que entra por la esquina de arriba a la izquierda y muere antes de
 * llegar al texto, y la insignia. Con eso sigue diciendo en qué estado está sin
 * salirse del sistema.
 */
.recomendacion {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: var(--blubathon-recomendacion-alto);
  padding: var(--blubathon-esp-16);
  background:
    radial-gradient(120% 130% at 0% 0%, var(--blubathon-rec-tinte), transparent 62%),
    var(--blubathon-superficie);
  border-radius: var(--blubathon-radio-24);
  box-shadow: var(--blubathon-elev-1);
}

/*
 * Alineado a la izquierda, no centrado: una frase de dos líneas centrada obliga
 * a buscar el principio de cada una, y aquí lo que se lee es la frase.
 */
.recomendacion__marca {
  display: flex;
  align-items: center;
  gap: var(--blubathon-esp-10);
  font-size: var(--blubathon-fs-11);
  font-weight: 700;
  letter-spacing: var(--blubathon-track-014);
  text-transform: uppercase;
  color: var(--blubathon-rec-sobretitulo);
}

.recomendacion__insignia {
  display: grid;
  flex: none;
  place-items: center;
  width: var(--blubathon-insignia);
  height: var(--blubathon-insignia);
  background: var(--blubathon-rec-insignia);
  border-radius: 50%;
}

.recomendacion__destello {
  width: var(--blubathon-icono-14);
  height: var(--blubathon-icono-14);
}

.recomendacion__frase {
  margin-top: var(--blubathon-esp-12);
  font-size: var(--blubathon-fs-17);
  font-weight: 700;
  line-height: 1.4;
  /* El mismo oscuro que los títulos de las otras tarjetas: sobre blanco, lo que
     manda es el sistema, no la banda. */
  color: var(--blubathon-marca-profundo);
}
</style>
