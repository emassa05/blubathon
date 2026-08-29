<script setup lang="ts">
import { onMounted, ref } from "vue";

import { revisarRecomendacion } from "@/api/blubathon";
import { mensajeDeError } from "@/api/cliente";
import ListaNinos from "@/components/terapeuta/ListaNinos.vue";
import ResumenConjuntoWidget from "@/components/terapeuta/ResumenConjunto.vue";
import RevisionRecomendacion from "@/components/terapeuta/RevisionRecomendacion.vue";
import { useTerapeuta } from "@/estado/terapeuta";

/**
 * El panel del terapeuta.
 *
 * Tres widgets: la cartera a la izquierda —quién hay y cómo va—, y a la derecha
 * la revisión de las recomendaciones de hoy encima del resumen del conjunto.
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
 * En móvil es una columna: lista, revisión, conjunto. Ese es el orden en que se
 * necesitan, y también el orden del DOM, así que la navegación por teclado y la
 * lectura secuencial coinciden con lo que se ve.
 */
.panel__reticula {
  display: flex;
  flex-direction: column;
  gap: var(--blubathon-esp-16);
  margin-top: var(--blubathon-esp-20);
}

/*
 * Escritorio: dos brazos dentro de una pantalla que no se desplaza. A la
 * izquierda quién hay y cómo va —la cartera, que ocupa las dos filas—; a la
 * derecha qué hay que hacer con eso hoy —la revisión— y qué se puede decir del
 * grupo.
 *
 * El panel mide exactamente la ventana y lo que sobra se desplaza **dentro** de
 * cada widget, no arrastrando la página. Es lo que distingue un panel de una
 * pantalla de lectura: aquí se compara, y comparar exige que la cartera siga a
 * la vista mientras se recorre la cola de recomendaciones. Con la página
 * desplazándose, bajar a la quinta recomendación dejaba fuera a los doce niños.
 *
 * `minmax(0, 1fr)` en la primera fila y `auto` en la segunda: el resumen del
 * conjunto mide lo que mide —son cuatro barras y cuatro cifras, no crece— y
 * todo lo que sobre es para la revisión.
 */
@media (min-width: 900px) {
  .panel {
    display: flex;
    flex-direction: column;
    height: 100dvh;
  }

  .panel__reticula {
    display: grid;
    flex: 1;
    grid-template-columns: minmax(0, var(--blubathon-columna-cartera)) minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr) auto;
    grid-template-areas:
      "lista revision"
      "lista conjunto";
    /* Sin esto, la altura mínima de una casilla es la de su contenido y los dos
       widgets altos empujarían la retícula por debajo del borde de la ventana. */
    min-block-size: 0;
    gap: var(--blubathon-esp-20);
  }

  /* La cartera llega hasta abajo aunque le sobre sitio: es la columna desde la
     que se mira todo lo demás, y una tarjeta que se corta a media altura parece
     el final de la lista y no el final de los niños. */
  .panel__zona--lista {
    grid-area: lista;
    min-block-size: 0;
  }

  .panel__zona--revision {
    grid-area: revision;
    min-block-size: 0;
  }

  .panel__zona--conjunto {
    grid-area: conjunto;
  }
}
</style>
