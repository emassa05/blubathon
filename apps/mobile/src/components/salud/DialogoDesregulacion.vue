<script setup lang="ts">
import { computed } from "vue";

import type { OutcomeRequestView } from "@/api/contrato";
import DialogoModal from "@/components/base/DialogoModal.vue";
import IconoAlerta from "@/components/icons/IconoAlerta.vue";
import IconoCheck from "@/components/icons/IconoCheck.vue";

const props = defineProps<{
  solicitud: OutcomeRequestView;
  enviando: boolean;
  error: string | null;
}>();

defineEmits<{ responder: [valor: "yes" | "no"] }>();

const FORMATO_HORA = new Intl.DateTimeFormat("es-ES", {
  weekday: "long",
  hour: "2-digit",
  minute: "2-digit",
});

const vencimiento = computed(() =>
  FORMATO_HORA.format(new Date(props.solicitud.capture_deadline_at)),
);
</script>

<template>
  <!--
    Obligatorio y centrado. No es una hoja: una hoja se apoya en el borde y se
    baja con el pulgar, y este diálogo no se baja. Está en el centro porque es
    lo único que hay que mirar, y no lleva aspa porque no hay nada que cerrar:
    la salida es contestar, y las dos respuestas están a un toque.
  -->
  <DialogoModal
    variante="centrado"
    :cerrable="false"
    :nivel="2"
    sobretitulo="Antes de seguir"
    :titulo="solicitud.question_es"
  >
    <div class="desregulacion">
      <p class="desregulacion__entrada">
        El día que registraste abrió esta pregunta. Contestarla es lo que hace que la próxima
        estimación salga de lo que de verdad pasó y no de lo que el modelo supuso.
      </p>

      <!-- Las anclas son la definición acordada de qué cuenta como episodio. Sin
           ellas cada persona respondería a una pregunta distinta. -->
      <ul v-if="solicitud.severity_anchors_es?.length" class="desregulacion__anclas">
        <li
          v-for="ancla in solicitud.severity_anchors_es"
          :key="ancla"
          class="desregulacion__ancla"
        >
          {{ ancla }}
        </li>
      </ul>

      <p class="desregulacion__plazo">Tienes hasta el {{ vencimiento }} para responder.</p>
    </div>

    <template #pie>
      <p v-if="error" class="desregulacion__error" role="alert">{{ error }}</p>

      <div class="desregulacion__acciones">
        <button
          type="button"
          class="desregulacion__boton desregulacion__boton--si"
          :disabled="enviando"
          @click="$emit('responder', 'yes')"
        >
          <IconoAlerta class="desregulacion__icono" aria-hidden="true" />
          Sí, ocurrió
        </button>

        <button
          type="button"
          class="desregulacion__boton desregulacion__boton--no"
          :disabled="enviando"
          @click="$emit('responder', 'no')"
        >
          <IconoCheck class="desregulacion__icono" aria-hidden="true" />
          No ocurrió
        </button>
      </div>
    </template>
  </DialogoModal>
</template>

<style scoped>
.desregulacion__entrada {
  font-size: var(--blubathon-fs-135);
  line-height: 1.5;
  color: var(--blubathon-marca-texto);
}

.desregulacion__anclas {
  margin-top: var(--blubathon-esp-14);
  padding: var(--blubathon-esp-4) var(--blubathon-esp-14);
  background: var(--blubathon-superficie);
  border-radius: var(--blubathon-radio-14);
}

.desregulacion__ancla {
  padding-block: var(--blubathon-esp-9);
  font-size: var(--blubathon-fs-125);
  line-height: 1.45;
  color: var(--blubathon-gris-texto);
}

.desregulacion__ancla + .desregulacion__ancla {
  border-top: 1px solid var(--blubathon-linea);
}

.desregulacion__plazo {
  margin-top: var(--blubathon-esp-14);
  font-size: var(--blubathon-fs-125);
  color: var(--blubathon-gris-texto);
}

.desregulacion__error {
  margin-bottom: var(--blubathon-esp-10);
  padding: var(--blubathon-esp-9) var(--blubathon-esp-12);
  font-size: var(--blubathon-fs-125);
  color: var(--blubathon-critica-alta-texto);
  background: var(--blubathon-critica-alta-fondo);
  border-radius: var(--blubathon-radio-14);
}

/* Envuelven en pantallas estrechas: dos áreas táctiles de 44 no caben en 320
   sin encogerse por debajo del mínimo. Es la misma regla de la tarjeta. */
.desregulacion__acciones {
  display: flex;
  flex-wrap: wrap;
  gap: var(--blubathon-esp-12);
}

.desregulacion__boton {
  display: flex;
  flex: 1 1 10rem;
  align-items: center;
  justify-content: center;
  gap: var(--blubathon-esp-9);
  min-height: var(--blubathon-toque);
  padding-inline: var(--blubathon-esp-14);
  font-size: var(--blubathon-fs-135);
  font-weight: 700;
  border-radius: var(--blubathon-radio-18);
}

.desregulacion__boton:disabled {
  opacity: 0.55;
}

.desregulacion__boton:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-foco-oscuro);
  outline-offset: var(--blubathon-foco-offset);
}

.desregulacion__boton--si {
  color: var(--blubathon-critica-alta-texto);
  background: var(--blubathon-critica-alta-fondo);
}

.desregulacion__boton--no {
  color: var(--blubathon-marca-accion);
  background: var(--blubathon-marca-icono-fondo);
}

.desregulacion__icono {
  flex: none;
  width: var(--blubathon-icono-16);
  height: var(--blubathon-icono-16);
}
</style>
