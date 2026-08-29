<script setup lang="ts">
/**
 * El botón de acción de la aplicación.
 *
 * Un solo sitio con la forma —área táctil de 44, radio 18, peso 700, icono y
 * rótulo centrados— y tres tonos que salen de la paleta que ya existe. Antes
 * cada pantalla se dibujaba el suyo, y dos botones que hacen lo mismo acababan
 * con dos alturas y dos radios distintos.
 *
 * El tono no es decoración: dice de qué familia es la respuesta. `marca` es la
 * acción neutra, `positivo` confirma y `negativo` avisa. Ninguno pesa más que
 * otro —todos son fondo suave con texto oscuro— porque en los sitios donde se
 * usan en pareja la elección no tiene opción por defecto.
 */
defineProps<{ tono: "marca" | "positivo" | "negativo" }>();
</script>

<template>
  <button type="button" class="boton" :class="`boton--${tono}`">
    <slot />
  </button>
</template>

<style scoped>
.boton {
  display: inline-flex;
  gap: var(--blubathon-esp-9);
  align-items: center;
  justify-content: center;
  min-height: var(--blubathon-toque);
  padding-inline: var(--blubathon-esp-14);
  font-size: var(--blubathon-fs-135);
  font-weight: 700;
  /* El filete es el mismo color del texto muy rebajado: da borde a un botón de
     fondo pálido sin meter un gris que no está en la paleta. */
  border: 1px solid color-mix(in oklab, currentcolor 20%, transparent);
  border-radius: var(--blubathon-radio-18);
}

.boton:disabled {
  cursor: progress;
  opacity: 0.55;
}

.boton:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-foco-oscuro);
  outline-offset: var(--blubathon-foco-offset);
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
