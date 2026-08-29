<script setup lang="ts">
import { computed, watch } from "vue";

import IconoDestello from "@/components/icons/IconoDestello.vue";
import { useMaquinaDeEscribir } from "@/composables/useMaquinaDeEscribir";
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
 * Lo que se ve mientras tanto no es una frase que diga que se está preparando:
 * es el destello girando y tres renglones con la forma que va a tener el texto
 * cuando llegue. Una frase de espera ocupa el sitio de la recomendación con algo
 * que hay que leer para descubrir que no dice nada; un hueco con la forma del
 * contenido dice "está viniendo esto" sin pedir que se lea. La frase sigue
 * estando para quien usa un lector de pantalla, que no ve girar nada.
 */
const redactando = computed(() => props.recomendacion.estado === "pendiente");

const { mostrado, escribiendo, poner, escribir } = useMaquinaDeEscribir(
  props.recomendacion.estado === "pendiente" ? "" : props.recomendacion.texto,
);

/**
 * Lo que todavía no se ha escrito, en transparente.
 *
 * Está en el DOM desde el primer carácter para que el párrafo ocupe desde el
 * principio el alto que va a tener acabado. Sin él, el texto crecería línea a
 * línea y empujaría hacia abajo todo lo que hay debajo en la columna: la
 * tarjeta de factores y la de formularios bailarían durante los dos segundos
 * del tecleo.
 */
const restante = computed(() => props.recomendacion.texto.slice(mostrado.value.length));

/**
 * Se teclea lo que **llega**, no lo que ya estaba.
 *
 * Venir de `pendiente` es exactamente eso: la redacción terminó mientras la
 * tarjeta estaba delante. Montar la pantalla en un día ya redactado no es que
 * llegue nada, y retecleando esa recomendación la pantalla diría que está
 * trabajando cuando no lo está.
 *
 * Y hojear tampoco cuenta, aunque el día de antes estuviera en espera: eso lo
 * resuelve `SaludView`, que da el día como clave y vuelve a montar la tarjeta
 * al cambiar de fecha, así que aquí `anterior` siempre es del mismo día.
 */
watch(
  () => props.recomendacion,
  (nueva, anterior) => {
    if (nueva.estado === "pendiente") {
      poner("");
      return;
    }
    if (anterior?.estado === "pendiente") {
      escribir(nueva.texto);
      return;
    }
    poner(nueva.texto);
  },
);
</script>

<template>
  <section class="recomendacion" :class="{ 'recomendacion--redactando': redactando }">
    <h2 class="recomendacion__marca">
      <span class="recomendacion__insignia" aria-hidden="true">
        <IconoDestello class="recomendacion__destello" />
      </span>
      <span>{{ SOBRETITULO }}</span>
    </h2>

    <!-- El párrafo que se ve es la animación del texto, no el texto: durante el
         tecleo cambia sesenta veces por segundo y anunciar cada fotograma
         dejaría el lector de pantalla hablando encima de sí mismo. Por eso va
         oculto al lector y el texto de verdad viaja abajo, en la región de
         estado, que lo anuncia una vez y entero. -->
    <p v-if="!redactando" class="recomendacion__frase" aria-hidden="true">
      <span class="recomendacion__escrito">{{ mostrado }}</span
      ><span v-if="escribiendo" class="recomendacion__cursor"></span
      ><span class="recomendacion__resto">{{ restante }}</span>
    </p>

    <div v-if="redactando" class="cargando" aria-hidden="true">
      <span class="cargando__renglon"></span>
      <span class="cargando__renglon"></span>
      <span class="cargando__renglon"></span>
    </div>

    <!-- Lo que se lee y no se ve: la espera mientras se redacta y la
         recomendación entera en cuanto llega, sin pasar por el tecleo. -->
    <p class="recomendacion__estado oculto-visual" role="status">{{ recomendacion.texto }}</p>
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

/*
 * Y el destello gira: es el indicador de que hay un modelo trabajando ahora
 * mismo. Gira dentro de su insignia, que no se mueve, así que no desplaza ni
 * un píxel del sobretítulo de al lado; es una transformación, o sea que el
 * compositor la resuelve sin `layout` ni `paint` en ningún fotograma.
 *
 * Vuelta y media por segundo: más rápido se lee como un error y más lento
 * parece que se ha quedado colgado.
 */
.recomendacion--redactando .recomendacion__destello {
  animation: recomendacion-gira 1.5s linear infinite;
}

@keyframes recomendacion-gira {
  to {
    transform: rotate(360deg);
  }
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

/* Lo que falta por escribir ocupa su sitio sin verse: reserva el alto del
   párrafo acabado para que nada de abajo se mueva mientras se teclea. */
.recomendacion__resto {
  color: transparent;
}

/*
 * El cursor, solo mientras se escribe. Va entre lo escrito y lo que falta, así
 * que se desplaza con el texto sin ocupar ancho propio en la línea acabada.
 */
.recomendacion__cursor {
  display: inline-block;
  width: 2px;
  height: 1em;
  vertical-align: -0.14em;
  background: currentcolor;
  border-radius: 1px;
  animation: recomendacion-latido 1s ease-in-out infinite;
}

@keyframes recomendacion-latido {
  0%,
  45% {
    opacity: 1;
  }

  55%,
  100% {
    opacity: 0;
  }
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
 * ahí, en gris fijo— y lo que se quita es el barrido, el giro y el parpadeo. El
 * texto no se teclea: `useMaquinaDeEscribir` lo pone entero, así que aquí no
 * queda cursor que apagar salvo el de un fotograma suelto.
 */
@media (prefers-reduced-motion: reduce) {
  .recomendacion--redactando .recomendacion__insignia,
  .recomendacion--redactando .recomendacion__destello,
  .recomendacion__cursor,
  .cargando__renglon {
    animation: none;
  }

  .cargando__renglon {
    background: var(--blubathon-linea);
  }
}
</style>
