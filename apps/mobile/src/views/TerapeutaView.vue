<script setup lang="ts">
import { onMounted, ref } from "vue";

import { revisarRecomendacion } from "@/api/blubathon";
import { mensajeDeError } from "@/api/cliente";
import ListaNinos from "@/components/terapeuta/ListaNinos.vue";
import PerfilNino from "@/components/terapeuta/PerfilNino.vue";
import ResumenConjuntoWidget from "@/components/terapeuta/ResumenConjunto.vue";
import RevisionRecomendacion from "@/components/terapeuta/RevisionRecomendacion.vue";
import { useTerapeuta } from "@/estado/terapeuta";

/**
 * El panel del terapeuta.
 *
 * Tres widgets: la cartera a la izquierda, y a la derecha la revisión de las
 * recomendaciones de hoy encima del resumen del conjunto. El perfil del niño
 * seleccionado cuelga de la columna izquierda, debajo de la lista, porque
 * pertenece a lo que se está mirando y no a lo que hay que decidir.
 *
 * Por qué la revisión va arriba a la derecha y no abajo: es lo único de la
 * pantalla que **caduca**. Las recomendaciones son de hoy, y una que nadie
 * revisó hoy ya no se puede revisar a tiempo. El resumen del conjunto sigue
 * siendo verdad mañana.
 */
const {
  fichas,
  cargandoCartera,
  errorCartera,
  cargarCartera,
  cola,
  cargandoCola,
  errorCola,
  cargarCola,
  seleccionado,
  seleccionar,
  ficha,
  conjunto,
} = useTerapeuta();

/** Id de la recomendación cuya decisión está en vuelo. */
const enviando = ref<string | null>(null);
const errorDecision = ref<string | null>(null);

onMounted(() => {
  // En paralelo: la cola no depende de la cartera y esperar a seis historiales
  // para enseñar la primera recomendación no ayudaría a nadie.
  void cargarCartera();
  void cargarCola();
});

async function decidir(id: string, decision: "approved" | "rejected"): Promise<void> {
  enviando.value = id;
  errorDecision.value = null;
  try {
    await revisarRecomendacion(id, { decision });
    // Se recarga la cola en vez de escribir la decisión en el objeto local: el
    // servidor es el que sabe cuál es la revisión vigente, y con dos pestañas
    // abiertas un estado local se quedaría contando otra cosa.
    await cargarCola();
  } catch (fallo) {
    errorDecision.value = mensajeDeError(fallo);
  } finally {
    enviando.value = null;
  }
}
</script>

<template>
  <main class="panel">
    <header class="panel__cabecera">
      <p class="panel__sobretitulo">Blubathon</p>
      <h1 class="panel__titulo">Panel del terapeuta</h1>
    </header>

    <p v-if="errorCartera" class="panel__aviso" role="alert">{{ errorCartera }}</p>
    <p v-if="errorDecision" class="panel__aviso" role="alert">{{ errorDecision }}</p>

    <div class="panel__reticula">
      <ListaNinos
        class="panel__zona--lista"
        :fichas="fichas"
        :seleccionado="seleccionado"
        :cargando="cargandoCartera"
        @seleccionar="seleccionar"
      />

      <PerfilNino v-if="ficha" class="panel__zona--perfil" :ficha="ficha" />

      <RevisionRecomendacion
        class="panel__zona--revision"
        :cola="cola"
        :cargando="cargandoCola"
        :error="errorCola"
        :enviando="enviando"
        @decidir="decidir"
      />

      <ResumenConjuntoWidget class="panel__zona--conjunto" :conjunto="conjunto" />
    </div>
  </main>
</template>

<style scoped>
.panel {
  min-height: 100dvh;
  padding: var(--blubathon-esp-20)
    max(var(--blubathon-esp-16), (100% - var(--blubathon-panel-ancho)) / 2)
    calc(var(--blubathon-esp-26) + env(safe-area-inset-bottom, 0px));
  background: var(--blubathon-fondo-final);
}

.panel__sobretitulo {
  font-size: var(--blubathon-fs-11);
  font-weight: 700;
  letter-spacing: var(--blubathon-track-014);
  text-transform: uppercase;
  color: var(--blubathon-gris-texto);
}

.panel__titulo {
  margin-top: var(--blubathon-esp-4);
  font-size: var(--blubathon-fs-26);
  font-weight: 700;
  letter-spacing: var(--blubathon-track-cifra);
  color: var(--blubathon-marca-profundo);
}

.panel__aviso {
  margin-top: var(--blubathon-esp-14);
  padding: var(--blubathon-esp-12) var(--blubathon-esp-16);
  font-size: var(--blubathon-fs-135);
  color: var(--blubathon-alerta-texto);
  background: var(--blubathon-alerta-fondo);
  border-radius: var(--blubathon-radio-18);
}

/*
 * En móvil es una columna: lista, perfil, revisión, conjunto. Ese es el orden
 * en que se necesitan, y también el orden del DOM, así que la navegación por
 * teclado y la lectura secuencial coinciden con lo que se ve.
 */
.panel__reticula {
  display: flex;
  flex-direction: column;
  gap: var(--blubathon-esp-16);
  margin-top: var(--blubathon-esp-20);
}

/*
 * Escritorio: dos brazos. A la izquierda quién es y cómo va —la cartera y el
 * perfil—; a la derecha qué hay que hacer con eso hoy —la revisión— y qué se
 * puede decir del grupo.
 *
 * Las casillas se declaran enteras y no por colocación automática: el perfil
 * desaparece cuando no hay nadie seleccionado, y con `auto-flow` esa ausencia
 * subiría la revisión a la fila del perfil y la retícula cambiaría de forma.
 */
@media (min-width: 900px) {
  .panel__reticula {
    display: grid;
    grid-template-columns: minmax(0, var(--blubathon-columna-cartera)) minmax(0, 1fr);
    grid-template-areas:
      "lista revision"
      "perfil conjunto"
      "perfil .";
    align-items: start;
    gap: var(--blubathon-esp-20);
  }

  .panel__zona--lista {
    grid-area: lista;
  }

  .panel__zona--perfil {
    grid-area: perfil;
  }

  .panel__zona--revision {
    grid-area: revision;
  }

  .panel__zona--conjunto {
    grid-area: conjunto;
  }
}
</style>
