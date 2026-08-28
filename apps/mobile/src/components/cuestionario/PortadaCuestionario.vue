<script setup lang="ts">
/**
 * La portada del cuestionario: progreso, de qué es, y una cara.
 *
 * En ese orden y de arriba abajo —los puntos, el rótulo con la fecha, y la cara
 * apoyada en la cúpula—, que es el mismo orden en el que se lee: por dónde vas,
 * qué estás contestando, y recién después el adorno.
 *
 * La cara se sortea al abrir y **vuelve a sortearse en cada paso**, nunca la
 * misma dos veces seguidas. Sale siempre una de las buenas —ver
 * `icons/mood/animos`—, así que cambiar de página cambia la cara pero no cambia
 * lo que la cara dice.
 */
import { shallowRef, watch } from "vue";

import { animoAlAzar } from "@/components/icons/mood/animos";

const props = withDefaults(
  defineProps<{
    /** Lo lleva el diálogo, que es quien nombra al `role="dialog"`. */
    idTitulo: string;
    /** Línea corta de arriba: de qué es esto. */
    sobretitulo?: string;
    titulo: string;
    /** El paso actual, empezando en 1. */
    paso?: number;
    /** Cuántos pasos hay. En 0 no se dibuja el progreso: ver abajo. */
    pasos?: number;
  }>(),
  { sobretitulo: "", paso: 1, pasos: 0 },
);

const animo = shallowRef(animoAlAzar());

watch(
  () => props.paso,
  () => {
    animo.value = animoAlAzar(animo.value);
  },
);
</script>

<template>
  <div class="portada">
    <!--
      El progreso desaparece cuando el formulario deja de tener pasos —el repaso
      final y la confirmación—, porque ahí no se avanza por páginas y unos puntos
      congelados se leerían como que algo se quedó a medias.

      Los puntos son decorativos y por dónde vas se dice con palabras: seis
      puntos se cuentan de uno en uno, y quien navega con lector no cuenta nada.
    -->
    <template v-if="pasos > 0">
      <p class="oculto-visual" aria-live="polite">Paso {{ paso }} de {{ pasos }}</p>

      <div class="portada__progreso" aria-hidden="true">
        <span
          v-for="numero in pasos"
          :key="numero"
          class="portada__punto"
          :class="{ 'portada__punto--actual': numero === paso }"
        ></span>
      </div>
    </template>

    <div class="portada__rotulos">
      <!-- El "(?)" va con el sobretítulo, que es el que nombra de qué es el
           diálogo, y no con el título, que aquí es la fecha. -->
      <p v-if="sobretitulo" class="portada__sobretitulo">
        {{ sobretitulo }}
        <slot name="ayuda" />
      </p>
      <h2 :id="idTitulo" class="portada__titulo">{{ titulo }}</h2>
    </div>

    <component :is="animo" class="portada__cara" />
  </div>
</template>

<style scoped>
/*
 * El mismo fondo que el panel de la pantalla de Salud: degradado casi blanco a
 * celeste, con un brillo abierto arriba. La receta está en `tokens.css`, en un
 * token propio: ver ahí por qué no se reusa la clase de banda.
 *
 * La cúpula de la que emerge el formulario no se dibuja aquí. Es el borde de
 * arriba del cuerpo del diálogo, que sube sobre esta portada y se recorta con
 * ella —ver `DialogoModal`—: así el arco no es un adorno encima de la portada
 * sino por donde se corta lo que se desplaza.
 */
.portada {
  position: relative;
  display: grid;
  justify-items: center;
  gap: var(--blubathon-esp-16);
  padding: var(--blubathon-esp-16) var(--blubathon-esp-16) var(--blubathon-esp-10);
  background: var(--blubathon-portada-fondo);
}

.portada__progreso,
.portada__rotulos {
  position: relative;
}

.portada__progreso {
  display: flex;
  align-items: center;
  gap: var(--blubathon-esp-8);
}

.portada__punto {
  width: var(--blubathon-punto);
  height: var(--blubathon-punto);
  background: var(--blubathon-portada-punto);
  border-radius: var(--blubathon-radio-pastilla);
  /* Cambiar de paso se ve: la pastilla se estira desde donde estaba en vez de
     aparecer ya estirada en el sitio de al lado. */
  transition:
    width var(--blubathon-dur-entrada) var(--blubathon-curva-hoja),
    background-color var(--blubathon-dur-entrada) var(--blubathon-curva-hoja);
}

/* El paso en el que estás no cambia solo de color: se alarga. El color por sí
   solo no distingue nada para quien no lo ve, y la forma sí. */
.portada__punto--actual {
  width: calc(var(--blubathon-punto) * 2.6);
  background: var(--blubathon-portada-paso);
}

.portada__rotulos {
  text-align: center;
}

/* Reserva el alto del "(?)": el disparador mide 44 de área táctil y se sube con
   márgenes negativos para no engordar la línea, así que sin este mínimo se
   derrama sobre la fecha, que aquí va justo debajo y centrada. */
.portada__sobretitulo {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: var(--blubathon-toque);
  font-size: var(--blubathon-fs-11);
  font-weight: 700;
  letter-spacing: var(--blubathon-track-012);
  text-transform: uppercase;
  color: var(--blubathon-portada-sobretitulo);
}

.portada__titulo {
  margin-top: var(--blubathon-esp-4);
  font-size: var(--blubathon-fs-17);
  font-weight: 700;
  color: var(--blubathon-portada-titulo);
}

/*
 * Se apoya en la cúpula: la parte de abajo cae sobre el blanco, que es lo que la
 * asienta en vez de dejarla flotando en el celeste.
 *
 * Y va en el plano de arriba del todo. El cuerpo, que es el que dibuja ese
 * blanco y llega hasta aquí por debajo de ella, va en el 1, y el filo que
 * difumina el arco en el 2 —ver `DialogoModal`—: aquí toca el 3. Sin él, lo que
 * se desplaza le pasaría por delante en vez de por detrás, y el difuminado le
 * comería el borde de abajo.
 */
.portada__cara {
  position: relative;
  z-index: 3;
  width: 84px;
  height: 84px;
  margin-top: var(--blubathon-esp-4);
}

@media (prefers-reduced-motion: reduce) {
  .portada__punto {
    transition: none;
  }
}

/* Ventana baja —el teléfono en horizontal—: la portada se aprieta hasta lo que
   sigue siendo reconocible, que es el rótulo. */
@media (max-height: 520px) {
  .portada {
    gap: var(--blubathon-esp-8);
    padding-block: var(--blubathon-esp-10) var(--blubathon-esp-6);
  }

  .portada__cara {
    width: 48px;
    height: 48px;
    margin-top: 0;
  }
}
</style>
