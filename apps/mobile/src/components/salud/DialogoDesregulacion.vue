<script setup lang="ts">
import type { OutcomeRequestView } from "@/api/contrato";
import DialogoModal from "@/components/base/DialogoModal.vue";
import IconoAlerta from "@/components/icons/IconoAlerta.vue";
import IconoCheck from "@/components/icons/IconoCheck.vue";

defineProps<{
  solicitud: OutcomeRequestView;
  enviando: boolean;
  error: string | null;
}>();

defineEmits<{ responder: [valor: "yes" | "no"] }>();

/**
 * La pregunta, en una línea.
 *
 * No se usa `solicitud.question_es`: el backend la redacta para el registro
 * —"…mayor…, según las anclas acordadas para esta demostración"— y eso son tres
 * renglones de condiciones que hay que leer enteros antes de poder contestar sí
 * o no. Lo que se pregunta es lo mismo; lo que cambia es que se lee de un
 * vistazo. La definición formal sigue siendo la del contrato y viaja intacta en
 * el reporte: aquí solo se decide cómo se enuncia en pantalla.
 */
const PREGUNTA = "¿Ocurrió una desregulación en las últimas 24 horas?";
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
    :titulo="PREGUNTA"
  >
    <!--
      Sin cuerpo: la pregunta es el título y las respuestas son el pie.

      Ni plazo ni anclas. El vencimiento es una regla del servidor y no algo que
      quien contesta pueda evitar, así que escribirlo solo metía prisa en la
      única pantalla donde la respuesta tiene que ser la verdadera y no la
      rápida. Y las anclas eran dos párrafos de definición encima de dos botones
      que ya dicen lo mismo: "sí, ocurrió" y "no ocurrió".
    -->
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
