<script setup lang="ts">
import type { Component } from "vue";

import IconoAlerta from "@/components/icons/IconoAlerta.vue";
import IconoLuna from "@/components/icons/IconoLuna.vue";
import IconoRombo from "@/components/icons/IconoRombo.vue";
import { AVISO_VARIABLES_CRITICAS, type VariableCritica } from "@/dominio/criticas";
import { ETIQUETA_PRIORIDAD, type IconoFactor } from "@/types/salud";

defineProps<{ criticas: readonly VariableCritica[] }>();

const ICONOS: Record<IconoFactor, Component> = {
  luna: IconoLuna,
  rombo: IconoRombo,
};
</script>

<template>
  <section class="criticas">
    <div class="criticas__cabecera">
      <span class="criticas__insignia" aria-hidden="true">
        <IconoAlerta class="criticas__glifo" />
      </span>
      <div>
        <h3 class="criticas__titulo">Variables críticas</h3>
        <p class="criticas__cuenta">
          {{ criticas.length }}
          {{ criticas.length === 1 ? "respuesta destacada" : "respuestas destacadas" }}
        </p>
      </div>
    </div>

    <ul class="criticas__lista">
      <li v-for="critica in criticas" :key="critica.campo" class="critica">
        <span class="critica__caja">
          <component :is="ICONOS[critica.icono]" class="critica__icono" />
        </span>

        <span class="critica__texto">
          <span class="critica__campo">{{ critica.titulo }}</span>
          <span class="critica__detalle">{{ critica.valor }} · {{ critica.motivo }}</span>
        </span>

        <span class="critica__pastilla" :class="`critica__pastilla--${critica.severidad}`">
          {{ ETIQUETA_PRIORIDAD[critica.severidad] }}
        </span>
      </li>
    </ul>

    <p class="criticas__pie">{{ AVISO_VARIABLES_CRITICAS }}</p>
  </section>
</template>

<style scoped>
/*
 * Misma tarjeta que las de Salud: superficie blanca, radio 24, elevación 1. Lo
 * que la distingue es la insignia de la cabecera, no una caja de color: un
 * bloque entero en naranja se lee como una alarma, y esto no es una alarma.
 */
.criticas {
  padding: var(--blubathon-esp-16);
  background: var(--blubathon-superficie);
  border-radius: var(--blubathon-radio-24);
  box-shadow: var(--blubathon-elev-1);
}

.criticas__cabecera {
  display: flex;
  align-items: center;
  gap: var(--blubathon-esp-12);
}

.criticas__insignia {
  display: grid;
  flex: none;
  place-items: center;
  width: var(--blubathon-insignia);
  height: var(--blubathon-insignia);
  color: var(--blubathon-critica-media-texto);
  background: var(--blubathon-critica-media-fondo);
  border-radius: 50%;
}

.criticas__glifo {
  width: var(--blubathon-icono-16);
  height: var(--blubathon-icono-16);
}

.criticas__titulo {
  font-size: var(--blubathon-fs-15);
  font-weight: 700;
  color: var(--blubathon-marca-profundo);
}

.criticas__cuenta {
  font-size: var(--blubathon-fs-125);
  color: var(--blubathon-gris-texto);
}

.criticas__lista {
  margin-top: var(--blubathon-esp-6);
}

.critica {
  display: flex;
  align-items: center;
  gap: var(--blubathon-esp-12);
  padding-block: var(--blubathon-esp-10);
}

.critica + .critica {
  border-top: 1px solid var(--blubathon-linea);
}

.critica__caja {
  display: grid;
  flex: none;
  place-items: center;
  width: var(--blubathon-caja-icono);
  height: var(--blubathon-caja-icono);
  color: var(--blubathon-marca-icono);
  background: var(--blubathon-marca-icono-fondo);
  border-radius: var(--blubathon-radio-10);
}

.critica__icono {
  width: var(--blubathon-icono-16);
  height: var(--blubathon-icono-16);
}

.critica__texto {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}

.critica__campo {
  font-size: var(--blubathon-fs-135);
  font-weight: 700;
  color: var(--blubathon-marca-titulo);
}

.critica__detalle {
  font-size: var(--blubathon-fs-125);
  color: var(--blubathon-gris-texto);
}

.critica__pastilla {
  flex: none;
  padding: var(--blubathon-esp-4) var(--blubathon-esp-9);
  font-size: var(--blubathon-fs-11);
  font-weight: 700;
  border-radius: var(--blubathon-radio-pastilla);
}

.critica__pastilla--alta {
  color: var(--blubathon-critica-alta-texto);
  background: var(--blubathon-critica-alta-fondo);
}

.critica__pastilla--media {
  color: var(--blubathon-critica-media-texto);
  background: var(--blubathon-critica-media-fondo);
}

.criticas__pie {
  margin-top: var(--blubathon-esp-10);
  font-size: var(--blubathon-fs-11);
  line-height: 1.45;
  color: var(--blubathon-gris-texto);
}
</style>
