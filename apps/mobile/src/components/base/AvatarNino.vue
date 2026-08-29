<script setup lang="ts">
import { computed } from "vue";

/**
 * La inicial de un niño en un disco de color.
 *
 * El color es identidad, no estado: sale de un hash de la semilla, así que el
 * mismo niño es del mismo tono en la cartera y en la cola de revisión, y dos
 * niños seguidos no se confunden al recorrer la columna. Por eso no lleva el
 * tono de la banda de riesgo: eso sí es estado, lo dice la cifra de al lado, y
 * un disco teñido de rojo junto a un porcentaje rojo diría lo mismo dos veces.
 *
 * Solo cambia el matiz. La claridad y el croma son fijos, así que el contraste
 * de la inicial sobre el disco es el mismo salga el hash que salga.
 */
const props = defineProps<{
  etiqueta: string;
  /** Qué se usa para sortear el matiz. Por defecto la propia etiqueta. */
  semilla?: string;
}>();

const iniciales = computed(() => {
  const palabras = props.etiqueta.split(/\s+/).filter((parte) => /\p{L}/u.test(parte));
  const primera = palabras[0]?.[0]?.toLocaleUpperCase("es") ?? "";
  /* Si la etiqueta lleva un número, ese número manda sobre la segunda inicial:
     en una cartera donde todos se llaman "Niña demo N", la segunda inicial es
     la misma para todos y el disco dejaría de distinguir a nadie. */
  const numero = /\d+/.exec(props.etiqueta)?.[0];
  return `${primera}${numero ?? palabras[1]?.[0]?.toLocaleUpperCase("es") ?? ""}`;
});

/**
 * El matiz, de 0 a 359.
 *
 * FNV-1a con la mezcla final de murmur3, y no una suma de caracteres: las
 * semillas son UUID que solo se diferencian en las últimas cifras, y un hash
 * sin avalancha les daba a todos matices consecutivos —230, 231, 232…— o sea
 * seis discos del mismo azul.
 */
const matiz = computed(() => {
  let mezcla = 2166136261;
  for (const caracter of props.semilla ?? props.etiqueta) {
    mezcla = Math.imul(mezcla ^ (caracter.codePointAt(0) ?? 0), 16777619);
  }
  mezcla = Math.imul(mezcla ^ (mezcla >>> 16), 2246822507);
  mezcla = Math.imul(mezcla ^ (mezcla >>> 13), 3266489909);
  return ((mezcla ^ (mezcla >>> 16)) >>> 0) % 360;
});
</script>

<template>
  <!-- Decorativo: el nombre está escrito al lado, y leer "ND" antes de "Niño
       demo 4" solo alarga la fila para quien usa un lector. -->
  <span class="avatar" :style="{ '--avatar-matiz': matiz }" aria-hidden="true">
    {{ iniciales }}
  </span>
</template>

<style scoped>
.avatar {
  display: grid;
  flex: none;
  place-items: center;
  width: var(--blubathon-avatar);
  height: var(--blubathon-avatar);
  font-size: var(--blubathon-fs-11);
  font-weight: 700;
  letter-spacing: var(--blubathon-track-012);
  color: oklch(0.42 0.09 var(--avatar-matiz));
  text-indent: var(--blubathon-track-012);
  background: oklch(0.88 0.06 var(--avatar-matiz));
  border-radius: 50%;
}
</style>
