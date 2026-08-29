<script setup lang="ts">
/**
 * El botón de la aplicación.
 *
 * Existe porque hasta ahora no existía: cada pantalla se dibujaba el suyo con
 * sus clases —`pie__enviar`, `sugerencia__usar`, `paginador__paso`— y eran
 * cinco pastillas parecidas pero no iguales, con cinco alturas, cinco radios y
 * cinco maneras de apagarse.
 *
 * Una sola forma —área táctil de 44, peso 700, icono y rótulo centrados— y una
 * lista cerrada de variantes, que son dos familias y no una escala:
 *
 * - **principal** y **secundario** ordenan. La llena cierra lo que se estaba
 *   haciendo —guardar el cuestionario, aceptar una sugerencia— y por eso solo
 *   debería haber una a la vista; la segunda tiene el mismo tamaño y la misma
 *   área táctil, sin relleno, y no es un "cancelar" ni un enlace: es una salida
 *   tan válida como la otra, solo que menos frecuente.
 * - **marca**, **positivo** y **negativo** no ordenan: dicen de qué familia es
 *   la respuesta. Todos son fondo suave con texto oscuro, y ninguno pesa más
 *   que otro a propósito, porque van en pareja —"sí ocurrió" y "no ocurrió",
 *   "estuvo bien" y "no estuvo bien"— y ahí la elección no puede tener opción
 *   por defecto: el botón grande se acabaría pulsando por ser el grande.
 *
 * `disabled`, `aria-*` y los oyentes llegan solos por atributos de caída, así
 * que no hay que declararlos aquí para poder usarlos fuera.
 */
withDefaults(
  defineProps<{
    variante?: "principal" | "secundario" | "marca" | "positivo" | "negativo";
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

/*
 * Los tres tonos van en pareja y dentro de una tarjeta, no en el pie de un
 * diálogo: por eso son más estrechos, con el radio de las piezas de tarjeta y
 * no el de pastilla, y con filete en vez de relleno. El filete es el mismo
 * color del texto muy rebajado, así da borde a un botón de fondo pálido sin
 * meter un gris que no está en la paleta.
 */
.boton--marca,
.boton--positivo,
.boton--negativo {
  gap: var(--blubathon-esp-9);
  padding-inline: var(--blubathon-esp-14);
  border: 1px solid color-mix(in oklab, currentcolor 20%, transparent);
  border-radius: var(--blubathon-radio-18);
}

/* Aquí apagado sí es esperar: los dos de la pareja se bloquean mientras la
   respuesta está en vuelo, y el cursor lo dice. */
.boton--marca:disabled,
.boton--positivo:disabled,
.boton--negativo:disabled {
  cursor: progress;
  opacity: 0.55;
}

.boton--marca {
  color: var(--blubathon-marca-accion);
  background: var(--blubathon-marca-icono-fondo);
}

.boton--positivo {
  color: var(--blubathon-exito-texto);
  background: var(--blubathon-exito-fondo);
}

.boton--negativo {
  color: var(--blubathon-critica-alta-texto);
  background: var(--blubathon-critica-alta-fondo);
}
</style>
