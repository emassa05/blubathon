<script setup lang="ts">
import SaludView from "@/views/SaludView.vue";
</script>

<template>
  <div class="lienzo">
    <SaludView class="lienzo__marco" />
    <!-- Solo en la vista de catálogo/preview: no forma parte de la app. -->
    <p class="lienzo__etiqueta">Salud</p>
  </div>
</template>

<style scoped>
.lienzo {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-height: 100dvh;
  background: var(--faro-lienzo);
}

.lienzo__etiqueta {
  display: none;
}

/* Mismo punto de corte que `SaludView`: ver `styles/tokens.css`. */
@media (min-width: 480px) {
  .lienzo {
    gap: var(--faro-esp-18);
    justify-content: center;
    padding: var(--faro-esp-30) var(--faro-esp-20);
  }

  .lienzo__marco {
    flex: none;
  }

  .lienzo__etiqueta {
    display: block;
    font-size: var(--faro-fs-15);
    font-weight: 600;
    letter-spacing: var(--faro-track-006);
    text-transform: uppercase;
    color: var(--faro-etiqueta-catalogo);
  }
}
</style>
