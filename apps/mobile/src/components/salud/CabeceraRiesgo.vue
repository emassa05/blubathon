<script setup lang="ts">
import { computed, toRef } from "vue";

import GloboAyuda from "@/components/base/GloboAyuda.vue";
import IconoEscudo from "@/components/icons/IconoEscudo.vue";
import { useNumeroAnimado } from "@/composables/useNumeroAnimado";

const props = defineProps<{
  /** Riesgo de desregulación, 0-100. `null` cuando el modelo se abstiene. */
  riesgo: number | null;
  /** Confianza del modelo en ese riesgo, 0-100. `null` si no hay estimación. */
  confianza: number | null;
}>();

const SOBRETITULO = "Riesgo de desregulación";

/** Sin cifra no se pone un cero: se dice que no la hay. */
const SIN_ESTIMACION = "—";

/*
 * La cifra sube hasta su valor en vez de aparecer puesta.
 *
 * Se anima la que se ve, no la del `aria-label`: un lector que anunciara los
 * cuarenta valores intermedios sería ilegible, así que el nombre accesible
 * salta directo al de destino.
 */
const { mostrado, reiniciar } = useNumeroAnimado(toRef(props, "riesgo"));

/*
 * Volver a contar desde cero no es cosa de la cabecera: no sabe que existe un
 * cuestionario ni cuándo se ha enviado. Se lo pide Salud, que sí lo sabe, y por
 * eso sale como método en vez de como prop.
 */
defineExpose({ animarDesdeCero: reiniciar });

/** Una sola etiqueta legible: "Riesgo de desregulación: 18 por ciento". */
const etiqueta = computed(() =>
  props.riesgo === null
    ? `${SOBRETITULO}: sin estimación todavía`
    : `${SOBRETITULO}: ${props.riesgo} por ciento`,
);
</script>

<template>
  <header class="riesgo">
    <!-- Las piezas visuales van en aria-hidden para que no se lea
         "Riesgo de desregulación 18%" suelto: el nombre accesible lo pone el
         aria-label, en el encabezado y en el grupo que pide el diseño.
         `heading-has-content` solo mira el contenido de texto del encabezado,
         no su aria-label, y por eso hay que silenciarlo justo aquí. -->
    <!-- eslint-disable-next-line vuejs-accessibility/heading-has-content -->
    <h1 class="riesgo__titulo" :aria-label="etiqueta">
      <span class="riesgo__grupo" role="group" :aria-label="etiqueta">
        <span class="riesgo__linea">
          <span class="riesgo__sobretitulo" aria-hidden="true">{{ SOBRETITULO }}</span>

          <GloboAyuda
            etiqueta="Qué significa el riesgo de desregulación"
            titulo="Qué es esta cifra"
            tono="panel"
            lado="izquierda"
          >
            <p>
              Es la proporción de días parecidos a hoy en los que sí hubo una desregulación, contada
              sobre los días de esta misma persona que ya se confirmaron.
            </p>
            <p>
              No es una predicción de lo que va a pasar, y no sale de un promedio de otras personas.
              Si todavía no hay días confirmados suficientes, no aparece ninguna cifra.
            </p>
          </GloboAyuda>
        </span>

        <!-- Sin espacios entre los dos tramos: la cifra y el signo son una sola
             palabra, y cualquier hueco aquí saldría también en el DOM. -->
        <span class="riesgo__cifra" aria-hidden="true"
          ><span>{{ mostrado ?? SIN_ESTIMACION }}</span
          ><span v-if="riesgo !== null" class="riesgo__porciento">%</span></span
        >
      </span>
    </h1>

    <!-- Sin estimación no hay confianza que dar: la pastilla desaparece en vez
         de mostrar un cero, que se leería como "confianza nula". -->
    <p v-if="confianza !== null" class="riesgo__confianza">
      <IconoEscudo class="riesgo__escudo" aria-hidden="true" />
      <span
        >Nivel de confianza <b class="riesgo__dato">{{ confianza }}%</b></span
      >
    </p>
  </header>
</template>

<style scoped>
.riesgo {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.riesgo__grupo {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.riesgo__linea {
  display: flex;
  align-items: center;
  /* En 320 con el texto ampliado, el sobretítulo y el "(?)" dejan de caber en
     una línea: envuelven centrados en vez de empujar el globo fuera. */
  flex-wrap: wrap;
  justify-content: center;
}

.riesgo__sobretitulo {
  font-size: var(--blubathon-fs-125);
  font-weight: 700;
  letter-spacing: var(--blubathon-track-014);
  text-transform: uppercase;
  color: var(--blubathon-texto-suave);
}

/*
 * La cifra crece con la ventana, pero nunca por encima de lo que cabe.
 *
 * El 6.5rem del diseño está dibujado para la columna de 480. En un teléfono de
 * 320 con tres dígitos —un riesgo de tres cifras— y el texto ampliado al 200%,
 * ese cuerpo se sale por los dos lados. `clamp` lo deja crecer hasta su medida
 * de siempre y lo encoge solo cuando el ancho no da: en 480 y en adelante el
 * valor es exactamente el de antes, así que el móvil validado no cambia.
 */
.riesgo__cifra {
  display: block;
  max-width: 100%;
  margin-top: var(--blubathon-esp-4);
  font-size: clamp(3.75rem, 21vw, var(--blubathon-fs-104));
  font-weight: 400;
  line-height: 1;
  letter-spacing: var(--blubathon-track-cifra);
  color: var(--blubathon-texto-fuerte);
  /* La cifra cambia de ancho al subir —de 8 a 88 hay un dígito de diferencia— y
     sin esto la cabecera entera se movería con cada fotograma. */
  font-variant-numeric: tabular-nums;
}

/*
 * El signo, a la mitad de la cifra. Es lo que la deja crecer: con el `%` del
 * mismo cuerpo, el bloque se come el ancho y hay que encoger el número, que es
 * justo el dato que se venía a leer. En `em` para que siga a la cifra sea cual
 * sea su tamaño.
 */
.riesgo__porciento {
  font-size: 0.46em;
  letter-spacing: 0;
}

/*
 * La confianza va en pastilla, no suelta: es un dato secundario y en vidrio se
 * lee sobre cualquier punto del gradiente, sin depender de dónde caiga.
 */
.riesgo__confianza {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: var(--blubathon-esp-8);
  max-width: 100%;
  margin-top: var(--blubathon-esp-14);
  padding: var(--blubathon-esp-8) var(--blubathon-esp-14);
  font-size: var(--blubathon-fs-125);
  font-weight: 600;
  color: var(--blubathon-texto-suave);
  background: var(--blubathon-vidrio);
  border: 1px solid var(--blubathon-vidrio-borde);
  border-radius: var(--blubathon-radio-pastilla);
}

.riesgo__dato {
  font-weight: 700;
  color: var(--blubathon-texto-fuerte);
  font-variant-numeric: tabular-nums;
}

.riesgo__escudo {
  flex: none;
  width: var(--blubathon-icono-14);
  height: var(--blubathon-icono-14);
}

/*
 * Teléfono en horizontal. La cifra se mide contra el alto y no contra el ancho:
 * lo que falta ahí no son píxeles a los lados —sobran— sino renglones. Con el
 * cuerpo de siempre, la cifra y su pastilla se comen la ventana entera y las
 * tarjetas empiezan fuera de la pantalla.
 */
@media (max-height: 520px) and (min-width: 600px) {
  .riesgo__cifra {
    font-size: clamp(2.75rem, 13dvh, var(--blubathon-fs-104));
  }

  .riesgo__confianza {
    margin-top: var(--blubathon-esp-8);
  }
}
</style>
