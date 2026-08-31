<script setup lang="ts">
import { computed, useId } from "vue";

import type { OutcomeRequestView } from "@/api/contrato";
import BotonAccion from "@/components/base/BotonAccion.vue";
import IconMoodSad from "@/components/icons/mood/IconMoodSad.vue";
import { ventanaEnPalabras } from "@/dominio/ventana";

const props = defineProps<{
  solicitud: OutcomeRequestView;
  enviando: boolean;
  error: string | null;
}>();

defineEmits<{
  reportar: [valor: "yes" | "no"];
}>();

/*
 * Puede haber dos tarjetas a la vez, así que el `id` del titular no puede ser
 * una constante: dos elementos con el mismo `id` dejan el `aria-labelledby` de
 * la segunda apuntando al titular de la primera.
 *
 * Y la región se nombra con el titular **y** el periodo. El titular solo es
 * idéntico en las dos —es la misma pregunta— y con eso quien navega por
 * regiones oye dos veces lo mismo sin manera de saber cuál es cuál. Es lo que
 * `landmark-unique` de axe comprueba.
 */
const idTitulo = useId();
const idVentana = useId();

/** De qué 24 horas habla esta pregunta. Es lo único que separa una tarjeta de
    la otra cuando hay dos. */
const ventana = computed(() => ventanaEnPalabras(props.solicitud));

/**
 * La pregunta, en una línea.
 *
 * No se usa `solicitud.question_es`: el backend la redacta para el registro
 * —"…mayor…, según las anclas acordadas para esta demostración"— y eso son tres
 * renglones de condiciones que hay que leer enteros antes de poder contestar sí
 * o no. Lo que se pregunta es lo mismo; lo que cambia es que se lee de un
 * vistazo. La definición formal sigue siendo la del contrato y viaja intacta en
 * el reporte: aquí solo se decide cómo se enuncia en pantalla.
 *
 * Tampoco dice ya "en las últimas 24 horas". Con dos preguntas abiertas a la
 * vez eso era falso en una de las dos —la de ayer habla de una ventana que
 * cerró hace horas, la de hoy de una que aún no ha terminado— y encima las
 * dejaba idénticas. El periodo va debajo, dicho entero.
 */
const PREGUNTA = "¿Ocurrió una desregulación?";
</script>

<template>
  <section class="resultado" :aria-labelledby="`${idTitulo} ${idVentana}`">
    <!--
      La cara, a caballo del borde de arriba: mitad dentro y mitad fuera. Es lo
      que separa esta tarjeta de las que solo informan —hasta que la pregunta no
      se contesta, el baseline se queda sin resultados verificados y el modelo
      no da cifra— y hace ese trabajo mejor que el sobretítulo que había antes,
      que era un rótulo naranja de 11px indistinguible de cualquier otro.

      Es decorativa: lo que hay que leer es la pregunta, que es el titular.
    -->
    <IconMoodSad class="resultado__cara" />

    <h2 :id="idTitulo" class="resultado__titulo">{{ PREGUNTA }}</h2>
    <p :id="idVentana" class="resultado__ventana">{{ ventana }}</p>

    <div class="resultado__acciones">
      <!--
        Una palabra cada uno. La pregunta está justo encima y completa, así que
        repetir "ocurrió" en los dos botones no añadía nada: lo que se elige es
        sí o no.

        El `aria-label` sí lo dice entero. Quien navega saltando de botón en
        botón no tiene la pregunta delante, y "sí" a secas no es una respuesta a
        nada. Empieza por el rótulo visible, que es lo que pide el criterio
        "etiqueta en el nombre".
      -->
      <BotonAccion
        variante="negativo"
        class="resultado__boton resultado__boton--si"
        aria-label="Sí, ocurrió"
        :disabled="enviando"
        @click="$emit('reportar', 'yes')"
      >
        Sí
      </BotonAccion>

      <!-- Las dos respuestas, siempre. Un "no" resuelve en cuanto se da: ver
           `report_is_eligible` en el dominio del backend. -->
      <BotonAccion
        variante="positivo"
        class="resultado__boton resultado__boton--no"
        aria-label="No ocurrió"
        :disabled="enviando"
        @click="$emit('reportar', 'no')"
      >
        No
      </BotonAccion>
    </div>

    <p v-if="error" class="resultado__error" role="alert">{{ error }}</p>
  </section>
</template>

<style scoped>
/*
 * Fuera de las bandas, igual que el aviso pendiente y por la misma razón: no
 * habla del riesgo del día sino de algo que falta por hacer. Va en elevación 2
 * porque pide una acción, no informa.
 *
 * Y por encima de eso, tres cosas que ninguna otra tarjeta tiene, porque
 * ninguna otra vence: el filete de acento en el borde de arriba, el lavado
 * naranja que entra por esa misma esquina, y el titular un cuerpo más grande.
 * Es el mismo naranja del aviso pendiente —no entra ningún color nuevo—, usado
 * aquí con más superficie porque esto sí tiene plazo.
 */
.resultado {
  /* El hueco para la mitad que sobresale. Va en el margen y no en el acolchado
     porque la cara tiene que salirse de la tarjeta, no caber dentro: sin esto
     se subiría encima de lo que haya justo antes, que es la pregunta anterior
     cuando hay dos. Encima de la primera no hay nada que esquivar, y la
     pantalla se lo descuenta. */
  margin-top: var(--blubathon-cierre-saliente);
  padding: var(--blubathon-esp-18) var(--blubathon-esp-16) var(--blubathon-esp-16);
  text-align: center;
  background:
    radial-gradient(120% 140% at 0% 0%, var(--blubathon-aviso-fondo), transparent 58%),
    var(--blubathon-superficie);
  border-top: 3px solid var(--blubathon-aviso-insignia);
  border-radius: var(--blubathon-radio-24);
  box-shadow: var(--blubathon-elev-2);
}

/*
 * La cara sube hasta quedar partida por el borde: la mitad de su alto, más el
 * acolchado de arriba de la tarjeta, que también hay que descontar.
 *
 * El collar es el mismo blanco de la superficie y se pinta con una sombra, que
 * no ocupa sitio: así la cara recorta el filete naranja en vez de apoyarse
 * encima de él, que es lo que la deja leerse como una pieza aparte y no como un
 * icono grande dentro de la tarjeta.
 */
.resultado__cara {
  display: block;
  width: var(--blubathon-cierre-cara);
  height: var(--blubathon-cierre-cara);
  margin: calc((var(--blubathon-cierre-cara) / 2 + var(--blubathon-esp-18)) * -1) auto
    var(--blubathon-esp-16);
  border-radius: 50%;
  box-shadow: 0 0 0 var(--blubathon-cierre-collar) var(--blubathon-superficie);
}

.resultado__titulo {
  font-size: var(--blubathon-fs-17);
  font-weight: 700;
  line-height: 1.3;
  color: var(--blubathon-marca-profundo);
}

/* El periodo, en gris y un cuerpo por debajo del titular: acompaña a la
   pregunta, no compite con ella. */
.resultado__ventana {
  margin-top: var(--blubathon-esp-4);
  font-size: var(--blubathon-fs-125);
  line-height: 1.4;
  color: var(--blubathon-gris-texto);
}

/* Envuelven en pantallas estrechas: dos áreas táctiles de 44 no caben en 320
   sin encogerse por debajo del mínimo. */
.resultado__acciones {
  display: flex;
  flex-wrap: wrap;
  gap: var(--blubathon-esp-12);
  margin-top: var(--blubathon-esp-16);
}

/* La forma y los tonos los pone `BotonAccion`; aquí solo se dice que los dos se
   reparten la fila y envuelven en pantallas estrechas. */
.resultado__boton {
  flex: 1 1 10rem;
}

.resultado__error {
  margin-top: var(--blubathon-esp-12);
  padding: var(--blubathon-esp-9) var(--blubathon-esp-12);
  font-size: var(--blubathon-fs-125);
  color: var(--blubathon-critica-alta-texto);
  background: var(--blubathon-critica-alta-fondo);
  border-radius: var(--blubathon-radio-14);
}
</style>
