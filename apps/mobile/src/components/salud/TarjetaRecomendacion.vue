<script setup lang="ts">
import { computed } from "vue";

import IconoDestello from "@/components/icons/IconoDestello.vue";
import type { Recomendacion } from "@/types/salud";

const props = defineProps<{
  recomendacion: Recomendacion;
}>();

const SOBRETITULO = "Recomendación de hoy";

/**
 * Mientras el RAG redacta.
 *
 * `pendiente` es el único estado que se mueve solo: el backend está recuperando
 * fragmentos y redactando encima, y la respuesta va a cambiar sin que nadie
 * toque nada. Los otros tres son finales y se pintan quietos.
 *
 * Lo que se anima no es un giro suelto en una esquina: son tres renglones con la
 * forma que va a tener el texto cuando llegue, más un pulso en la insignia. Un
 * hueco con la forma del contenido dice "está viniendo esto"; un indicador
 * genérico solo dice "espera".
 */
const redactando = computed(() => props.recomendacion.estado === "pendiente");
</script>

<template>
  <section class="recomendacion" :class="{ 'recomendacion--redactando': redactando }">
    <h2 class="recomendacion__marca">
      <span class="recomendacion__insignia" aria-hidden="true">
        <IconoDestello class="recomendacion__destello" />
      </span>
      <span>{{ SOBRETITULO }}</span>
    </h2>

    <!-- El texto sigue estando en el DOM mientras se redacta, en un `role`
         que lo anuncia cuando cambie: quien usa un lector oye "estamos
         preparando la recomendación" y después la recomendación, sin tener que
         volver a buscarla. -->
    <p class="recomendacion__frase" role="status">{{ recomendacion.texto }}</p>

    <div v-if="redactando" class="cargando" aria-hidden="true">
      <span class="cargando__renglon"></span>
      <span class="cargando__renglon"></span>
      <span class="cargando__renglon"></span>
    </div>
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

/* Mientras se redacta, la insignia respira. Solo opacidad: no mueve ni
   redimensiona nada, así que no arrastra al texto de al lado. */
.recomendacion--redactando .recomendacion__insignia {
  animation: recomendacion-respira 1.6s ease-in-out infinite;
}

@keyframes recomendacion-respira {
  0%,
  100% {
    opacity: 1;
  }

  50% {
    opacity: 0.5;
  }
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

/* La frase de espera no compite con una recomendación de verdad: mientras se
   redacta es texto de apoyo, y el peso vuelve en cuanto llega la buena. */
.recomendacion--redactando .recomendacion__frase {
  font-size: var(--blubathon-fs-135);
  font-weight: 600;
  color: var(--blubathon-gris-texto);
}

/*
 * Los renglones que se están escribiendo.
 *
 * Tres, de anchos distintos y el último corto, que es la forma que tiene un
 * párrafo de dos líneas y media. Cada uno arranca su barrido un poco después
 * que el anterior, así que el conjunto se lee como algo que avanza de arriba
 * abajo y no como tres cosas parpadeando a la vez.
 *
 * El barrido es un `background-position` sobre un degradado, o sea una sola
 * propiedad compuesta por el compositor: no hay `layout` ni `paint` en ningún
 * fotograma.
 */
.cargando {
  display: flex;
  flex-direction: column;
  gap: var(--blubathon-esp-8);
  margin-top: var(--blubathon-esp-12);
}

.cargando__renglon {
  height: var(--blubathon-esp-10);
  background: linear-gradient(
    90deg,
    var(--blubathon-linea) 0%,
    var(--blubathon-fila-activa) 40%,
    var(--blubathon-linea) 80%
  );
  background-size: 220% 100%;
  border-radius: var(--blubathon-radio-pastilla);
  animation: cargando-barrido 1.4s linear infinite;
}

.cargando__renglon:nth-child(2) {
  animation-delay: 0.16s;
}

.cargando__renglon:nth-child(3) {
  width: 62%;
  animation-delay: 0.32s;
}

@keyframes cargando-barrido {
  from {
    background-position: 120% 0;
  }

  to {
    background-position: -120% 0;
  }
}

/*
 * Quien pide menos movimiento sigue viendo que falta algo —los renglones están
 * ahí, en gris fijo— y lo que se quita es el barrido. La frase de estado lo dice
 * escrito de todas formas.
 */
@media (prefers-reduced-motion: reduce) {
  .recomendacion--redactando .recomendacion__insignia,
  .cargando__renglon {
    animation: none;
  }

  .cargando__renglon {
    background: var(--blubathon-linea);
  }
}
</style>
