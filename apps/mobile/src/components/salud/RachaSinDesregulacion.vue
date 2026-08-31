<script setup lang="ts">
/**
 * Días seguidos sin un episodio confirmado.
 *
 * Va en el panel, justo debajo de la cifra de riesgo, y no en una tarjeta más
 * abajo. Las dos hablan de lo mismo —de episodios de desregulación— y una mira
 * hacia delante mientras la otra mira hacia atrás: leídas juntas, la racha es el
 * contexto que le falta a la cifra sola. Separarlas obligaría a desplazarse para
 * comparar lo que se estima con lo que de verdad ha estado pasando.
 *
 * La cifra sube al llegar, como la del riesgo y por la misma razón: es la única
 * buena noticia de la pantalla y merece que se la vea llegar.
 */
import { computed, toRef } from "vue";

import { useNumeroAnimado } from "@/composables/useNumeroAnimado";
import { etiquetaDiaLargo } from "@/dominio/semana";
import type { RachaSinDesregulacion } from "@/types/salud";

const props = defineProps<{ racha: RachaSinDesregulacion }>();

const dias = computed(() => props.racha.dias);
const { mostrado } = useNumeroAnimado(toRef(dias, "value"));

const palabra = computed(() => (props.racha.dias === 1 ? "día" : "días"));

/**
 * La racha se cuenta hasta el último día confirmado, no hasta hoy, porque la
 * pregunta de hoy suele seguir abierta. Decirlo es lo que impide leer la cifra
 * como "llevamos tantos días bien contando el de hoy".
 */
const hasta = computed(() => etiquetaDiaLargo(props.racha.hasta).toLowerCase());

const etiqueta = computed(() =>
  props.racha.dias === 0
    ? `El último día confirmado, ${hasta.value}, sí hubo un episodio de desregulación`
    : `${props.racha.dias} ${palabra.value} seguidos sin episodios de desregulación, contados hasta el ${hasta.value}`,
);
</script>

<template>
  <p class="racha">
    <!-- La frase entera y en palabras: la pastilla se lee de una vez, no cifra
         suelta y rótulo suelto. Va en un `span` oculto y no en un `aria-label`
         porque un `<p>` no tiene rol y no admite nombre accesible. -->
    <span class="oculto-visual">{{ etiqueta }}</span>
    <span aria-hidden="true" class="racha__cuerpo">
      <!-- Cero no se esconde: que la última confirmación fuera un "sí" es tan
           informativo como una racha larga, y desaparecer ahí dejaría el
           contador como algo que solo sale cuando las cosas van bien. -->
      <template v-if="racha.dias === 0">
        <span class="racha__rotulo">Último día confirmado</span>
        <span class="racha__texto">con episodio</span>
      </template>
      <template v-else>
        <b class="racha__cifra">{{ mostrado }}</b>
        <span class="racha__texto">{{ palabra }} sin desregulación</span>
      </template>
    </span>
  </p>
</template>

<style scoped>
/*
 * Texto suelto, sin pastilla. Dos superficies de vidrio seguidas —la confianza y
 * esto— se leían como dos etiquetas del mismo tipo, y no lo son: una acompaña a
 * la cifra de arriba y la otra es un dato por su cuenta. Lo que la hace resaltar
 * es la tinta fuerte de la banda y el peso, no una caja alrededor.
 */
.racha {
  display: flex;
  align-items: center;
  justify-content: center;
  max-width: 100%;
  margin-top: var(--blubathon-esp-10);
}

.racha__cuerpo {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: center;
  gap: var(--blubathon-esp-6);
}

.racha__cifra {
  font-size: var(--blubathon-fs-20);
  font-weight: 700;
  line-height: 1.2;
  color: var(--blubathon-texto-fuerte);
  font-variant-numeric: tabular-nums;
}

/*
 * Sin caja detrás, el rótulo tiene que sostenerse solo sobre el gradiente: sube
 * a la tinta fuerte de la banda —la misma de la cifra grande— en vez de quedarse
 * en el gris suave que usaba dentro de la pastilla.
 */
.racha__rotulo,
.racha__texto {
  font-size: var(--blubathon-fs-135);
  font-weight: 700;
  color: var(--blubathon-texto-fuerte);
}
</style>
