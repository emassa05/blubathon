<script setup lang="ts">
import { computed } from "vue";

import type { OutcomeRequestView } from "@/api/contrato";
import IconoCheck from "@/components/icons/IconoCheck.vue";
import IconoAlerta from "@/components/icons/IconoAlerta.vue";
import { ventanaCerrada } from "@/estado/resultados";

const props = defineProps<{
  solicitud: OutcomeRequestView;
  enviando: boolean;
  error: string | null;
}>();

defineEmits<{
  reportar: [valor: "yes" | "no"];
}>();

/**
 * Mientras la ventana de 24 h sigue abierta, "no ocurrió" todavía no se puede
 * afirmar: el día no ha terminado. Y SPEC 4.4 solo acepta un `no` reportado
 * `on_time`, así que uno enviado antes se guardaría sin resolver nada. El botón
 * no se ofrece hasta que resolvería de verdad.
 */
const puedeDecirQueNo = computed(() => ventanaCerrada(props.solicitud));

const FORMATO_HORA = new Intl.DateTimeFormat("es-ES", {
  weekday: "long",
  hour: "2-digit",
  minute: "2-digit",
});

const cierre = computed(() => FORMATO_HORA.format(new Date(props.solicitud.target_end_at)));
const vencimiento = computed(() =>
  FORMATO_HORA.format(new Date(props.solicitud.capture_deadline_at)),
);
</script>

<template>
  <section class="resultado" aria-labelledby="resultado-titulo">
    <p class="resultado__etiqueta">Resultado pendiente</p>
    <h2 id="resultado-titulo" class="resultado__titulo">{{ solicitud.question_es }}</h2>

    <!-- Las anclas son la definición acordada de qué cuenta como episodio. Sin
         ellas cada persona respondería a una pregunta distinta. -->
    <ul v-if="solicitud.severity_anchors_es?.length" class="resultado__anclas">
      <li v-for="ancla in solicitud.severity_anchors_es" :key="ancla" class="resultado__ancla">
        {{ ancla }}
      </li>
    </ul>

    <div class="resultado__acciones">
      <button
        type="button"
        class="resultado__boton resultado__boton--si"
        :disabled="enviando"
        @click="$emit('reportar', 'yes')"
      >
        <IconoAlerta class="resultado__icono" aria-hidden="true" />
        Sí, ocurrió
      </button>

      <button
        v-if="puedeDecirQueNo"
        type="button"
        class="resultado__boton resultado__boton--no"
        :disabled="enviando"
        @click="$emit('reportar', 'no')"
      >
        <IconoCheck class="resultado__icono" aria-hidden="true" />
        No ocurrió
      </button>
    </div>

    <p v-if="!puedeDecirQueNo" class="resultado__nota">
      El día todavía no termina. Podrás confirmar que no ocurrió a partir del {{ cierre }}, y tienes
      hasta el {{ vencimiento }} para responder.
    </p>
    <p v-else class="resultado__nota">Tienes hasta el {{ vencimiento }} para responder.</p>

    <p v-if="error" class="resultado__error" role="alert">{{ error }}</p>
  </section>
</template>

<style scoped>
/*
 * Fuera de las bandas, igual que el aviso pendiente y por la misma razón: no
 * habla del riesgo del día sino de algo que falta por hacer. Va en elevación 2
 * porque pide una acción, no informa.
 */
.resultado {
  padding: var(--faro-esp-16);
  background: var(--faro-superficie);
  border-radius: var(--faro-radio-24);
  box-shadow: var(--faro-elev-2);
}

.resultado__etiqueta {
  font-size: var(--faro-fs-11);
  font-weight: 700;
  letter-spacing: var(--faro-track-012);
  text-transform: uppercase;
  color: var(--faro-aviso-etiqueta);
}

.resultado__titulo {
  margin-top: var(--faro-esp-6);
  font-size: var(--faro-fs-155);
  font-weight: 700;
  line-height: 1.3;
  color: var(--faro-verde-profundo);
}

.resultado__anclas {
  margin-top: var(--faro-esp-12);
}

.resultado__ancla {
  padding-block: var(--faro-esp-6);
  font-size: var(--faro-fs-125);
  line-height: 1.45;
  color: var(--faro-gris-texto);
}

.resultado__ancla + .resultado__ancla {
  border-top: 1px solid var(--faro-linea);
}

/* Envuelven en pantallas estrechas: dos áreas táctiles de 44 no caben en 320
   sin encogerse por debajo del mínimo. */
.resultado__acciones {
  display: flex;
  flex-wrap: wrap;
  gap: var(--faro-esp-12);
  margin-top: var(--faro-esp-16);
}

.resultado__boton {
  display: flex;
  flex: 1 1 10rem;
  align-items: center;
  justify-content: center;
  gap: var(--faro-esp-9);
  min-height: var(--faro-toque);
  padding-inline: var(--faro-esp-14);
  font-size: var(--faro-fs-135);
  font-weight: 700;
  border-radius: var(--faro-radio-18);
}

.resultado__boton:disabled {
  opacity: 0.55;
}

.resultado__boton:focus-visible {
  outline: var(--faro-foco-grosor) solid var(--faro-foco-oscuro);
  outline-offset: var(--faro-foco-offset);
}

.resultado__boton--si {
  color: var(--faro-critica-alta-texto);
  background: var(--faro-critica-alta-fondo);
}

.resultado__boton--no {
  color: var(--faro-verde-accion);
  background: var(--faro-verde-icono-fondo);
}

.resultado__icono {
  flex: none;
  width: var(--faro-icono-16);
  height: var(--faro-icono-16);
}

.resultado__nota {
  margin-top: var(--faro-esp-12);
  font-size: var(--faro-fs-125);
  line-height: 1.45;
  color: var(--faro-gris-texto);
}

.resultado__error {
  margin-top: var(--faro-esp-12);
  padding: var(--faro-esp-9) var(--faro-esp-12);
  font-size: var(--faro-fs-125);
  color: var(--faro-critica-alta-texto);
  background: var(--faro-critica-alta-fondo);
  border-radius: var(--faro-radio-14);
}
</style>
