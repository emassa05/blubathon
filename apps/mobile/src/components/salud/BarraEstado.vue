<script setup lang="ts">
defineProps<{
  /** Hora en formato HH:mm. */
  hora: string;
  /** Carga de la batería, 0-100. */
  bateria: number;
}>();
</script>

<template>
  <div class="barra">
    <time class="barra__hora" :datetime="hora">{{ hora }}</time>

    <div class="barra__bateria" role="img" :aria-label="`Batería al ${bateria} por ciento`">
      <span class="barra__nivel" aria-hidden="true">{{ bateria }}</span>
      <span class="barra__pastilla" aria-hidden="true">
        <span class="barra__relleno" :style="{ width: `${bateria}%` }"></span>
      </span>
    </div>
  </div>
</template>

<style scoped>
.barra {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--faro-barra-alto);
  padding-inline: var(--faro-esp-30);
  color: #fff;
  letter-spacing: var(--faro-track-barra);
}

.barra__hora {
  font-size: var(--faro-fs-15);
  font-weight: 600;
}

.barra__bateria {
  display: flex;
  align-items: center;
  gap: var(--faro-esp-6);
}

.barra__nivel {
  font-size: var(--faro-fs-13);
  font-weight: 600;
}

.barra__pastilla {
  display: block;
  width: var(--faro-bateria-ancho);
  height: var(--faro-bateria-alto);
  padding: 1px;
  border: var(--faro-bateria-borde) solid rgb(255 255 255 / 0.75);
  border-radius: var(--faro-radio-4);
}

.barra__relleno {
  display: block;
  height: 100%;
  background: #fff;
  border-radius: 1px;
}
</style>
