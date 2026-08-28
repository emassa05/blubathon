<script setup lang="ts">
/**
 * El botón de la aplicación.
 *
 * Existe porque hasta ahora no existía: cada pantalla se dibujaba el suyo con
 * sus clases —`pie__enviar`, `sugerencia__usar`, `paginador__paso`— y eran
 * cinco pastillas parecidas pero no iguales, con cinco alturas, cinco radios y
 * cinco maneras de apagarse. Aquí hay dos, y las dos son la misma pieza:
 *
 * - **principal**: la llena. Es la que cierra lo que se estaba haciendo —guardar
 *   el cuestionario, aceptar una sugerencia— y por eso solo debería haber una a
 *   la vista.
 * - **secundaria**: el mismo tamaño y la misma área táctil, sin relleno. No es
 *   un "cancelar" ni un enlace: es una salida tan válida como la otra, solo que
 *   menos frecuente.
 *
 * `disabled`, `aria-*` y los oyentes llegan solos por atributos de caída, así
 * que no hay que declararlos aquí para poder usarlos fuera.
 */
withDefaults(
  defineProps<{
    variante?: "principal" | "secundario";
    /** Ocupa todo el ancho disponible. El pie del diálogo lo usa. */
    bloque?: boolean;
    /** El alto de una respuesta, para el botón que cierra el cuestionario. */
    grande?: boolean;
  }>(),
  { variante: "principal", bloque: false, grande: false },
);
</script>

<template>
  <button
    type="button"
    class="boton"
    :class="[`boton--${variante}`, { 'boton--bloque': bloque, 'boton--grande': grande }]"
  >
    <slot />
  </button>
</template>

<style scoped>
.boton {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--blubathon-esp-8);
  min-height: var(--blubathon-toque);
  padding-inline: var(--blubathon-esp-22);
  font-size: var(--blubathon-fs-135);
  font-weight: 700;
  border-radius: var(--blubathon-radio-pastilla);
}

.boton:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-foco-oscuro);
  outline-offset: var(--blubathon-foco-offset);
}

.boton--bloque {
  width: 100%;
}

/* Las mismas medidas que `OpcionRespuesta`: el que cierra el formulario no puede
   ser más chico que cualquiera de las respuestas que hay encima. */
.boton--grande {
  min-height: 56px;
  padding-inline: var(--blubathon-esp-18);
  font-size: var(--blubathon-fs-15);
}

.boton--principal {
  color: var(--blubathon-superficie);
  background: var(--blubathon-verde-accion);
  box-shadow: var(--blubathon-elev-1);
}

.boton--principal:hover:not(:disabled) {
  background: var(--blubathon-verde-accion-fuerte);
}

/*
 * Apagado no es desvanecido: sigue ocupando su sitio y sigue leyéndose, para que
 * el pie no cambie de forma cuando todavía no se puede guardar.
 */
.boton--principal:disabled {
  color: var(--blubathon-gris-texto);
  background: var(--blubathon-punto-inactivo);
  box-shadow: none;
  cursor: default;
}

.boton--secundario {
  padding-inline: var(--blubathon-esp-18);
  color: var(--blubathon-verde-accion);
  background: var(--blubathon-superficie);
  border: 1px solid var(--blubathon-linea);
}

.boton--secundario:hover:not(:disabled) {
  border-color: var(--blubathon-verde-accion);
}

.boton--secundario:disabled {
  color: var(--blubathon-punto-inactivo);
  cursor: default;
}
</style>
