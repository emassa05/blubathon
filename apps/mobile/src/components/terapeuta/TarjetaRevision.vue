<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, useTemplateRef, watch } from "vue";

import type { RecommendationInstanceView } from "@/api/contrato";
import AvatarNino from "@/components/base/AvatarNino.vue";
import BotonAccion from "@/components/base/BotonAccion.vue";
import IconoFlecha from "@/components/icons/IconoFlecha.vue";
import { BANDA_DE_LA_API, CLASE_BANDA, type BandaRiesgo } from "@/theme/riesgo";
import { ETIQUETA_DECISION } from "@/types/terapeuta";

const props = defineProps<{
  item: RecommendationInstanceView;
  /** El último riesgo estimado del niño, 0-100, o `null` si el modelo se abstiene. */
  riesgo: number | null;
  /** Hay una decisión en vuelo en el widget: se bloquean todos los pares. */
  enviando: boolean;
}>();

const emitir = defineEmits<{
  decidir: [id: string, decision: "approved" | "rejected"];
  verPerfil: [id: string];
}>();

const abierto = ref(false);

/**
 * ¿Hace falta el "Leer más"?
 *
 * Se mide, no se estima por número de caracteres: el recorte lo hace el CSS a
 * tres renglones, y cuántas palabras caben en tres renglones depende del ancho
 * de la columna, que cambia con la ventana. Con un umbral de caracteres, la
 * misma recomendación enseñaba un "Leer más" que no abría nada en pantalla
 * ancha y lo escondía en pantalla estrecha.
 */
const parrafo = useTemplateRef<HTMLElement>("parrafo");
const recortable = ref(false);

function medir(): void {
  const elemento = parrafo.value;
  if (elemento === null) return;
  // Con el párrafo abierto ya no hay recorte que medir, y la respuesta sigue
  // siendo la de antes de abrirlo.
  if (abierto.value) return;
  recortable.value = elemento.scrollHeight > elemento.clientHeight + 1;
}

let observador: ResizeObserver | null = null;

onMounted(() => {
  medir();
  observador = new ResizeObserver(medir);
  if (parrafo.value !== null) observador.observe(parrafo.value);
});

onBeforeUnmount(() => {
  observador?.disconnect();
  observador = null;
});

// La cola se recarga entera al decidir, así que la misma tarjeta puede pasar a
// llevar otro texto sin desmontarse.
watch(
  () => props.item.action_text_es,
  () => {
    abierto.value = false;
    void Promise.resolve().then(medir);
  },
);

const banda = computed(() => BANDA_DE_LA_API[props.item.risk_band]);

const ETIQUETA_BANDA: Record<BandaRiesgo, string> = {
  alto: "Riesgo alto",
  medio: "Riesgo medio",
  bajo: "Riesgo bajo",
  desconocido: "Sin estimación",
};

/** "Riesgo medio · 33%", con la abstención dicha y no dibujada como un cero. */
const estado = computed(() => {
  const cifra = props.riesgo === null ? "s/d" : `${Math.round(props.riesgo)}%`;
  return `${ETIQUETA_BANDA[banda.value]} · ${cifra}`;
});

const texto = computed(() => props.item.action_text_es ?? "Sin texto redactado.");

/** Ya decidida: la tarjeta sigue en la lista, con su veredicto, hasta que se
 *  recargue la cola. Sacarla al instante haría dudar de si el clic llegó. */
const decidida = computed(() => props.item.review_decision ?? null);
</script>

<template>
  <!--
    La banda del niño va en la tarjeta y no en un punto de color: de ahí sale el
    lavado del fondo, que es el mismo recurso con el que la pantalla del cuidador
    marca lo que ha escrito la IA. Aquí además dice de un vistazo cuál de las
    recomendaciones de la cola es la del niño que peor va.
  -->
  <article class="tarjeta" :class="CLASE_BANDA[banda]">
    <header class="tarjeta__cabecera">
      <AvatarNino
        class="tarjeta__avatar"
        :etiqueta="item.child_label ?? 'Niño sin etiqueta'"
        :semilla="item.child_id"
      />

      <div class="tarjeta__quien">
        <p class="tarjeta__nombre">{{ item.child_label ?? "Niño sin etiqueta" }}</p>
        <p class="tarjeta__estado">{{ estado }}</p>
      </div>

      <button type="button" class="tarjeta__perfil" @click="emitir('verPerfil', item.child_id)">
        Ver perfil
      </button>
    </header>

    <p ref="parrafo" class="tarjeta__texto" :class="{ 'tarjeta__texto--recortado': !abierto }">
      {{ texto }}
    </p>

    <p v-if="abierto && item.purpose_es" class="tarjeta__proposito">{{ item.purpose_es }}</p>

    <button
      v-if="recortable"
      type="button"
      class="tarjeta__mas"
      :aria-expanded="abierto"
      @click="abierto = !abierto"
    >
      {{ abierto ? "Leer menos" : "Leer más" }}
      <IconoFlecha class="tarjeta__flecha" :class="{ 'tarjeta__flecha--atras': abierto }" />
    </button>

    <!--
      Las citas no son adorno: la recomendación solo existe si cada afirmación
      salió de un fragmento del corpus, y lo que el profesional está juzgando es
      exactamente eso. Por eso no se esconden detrás del "Leer más" como el
      resto del texto: sin la fuente delante, responder sería firmar a ciegas.
    -->
    <ul v-if="item.citations?.length" class="citas">
      <li v-for="(cita, i) in item.citations" :key="i" class="citas__cita">
        <p class="citas__texto">«{{ cita.quote_es }}»</p>
        <p class="citas__fuente">{{ cita.document_title_es }} · {{ cita.locator }}</p>
      </li>
    </ul>

    <p v-if="decidida" class="veredicto" :class="`veredicto--${decidida}`" role="status">
      {{ ETIQUETA_DECISION[decidida] }}
    </p>

    <!--
      Los dos con el mismo peso visual. "Estuvo bien" no es la opción por defecto
      ni la deseable: si pesara más, la revisión derivaría en pulsar el grande,
      que es justamente la fatiga de decisión que la muestra existe para evitar.
    -->
    <div v-else class="tarjeta__acciones">
      <BotonAccion
        tono="positivo"
        class="tarjeta__boton tarjeta__boton--bien"
        :disabled="enviando"
        @click="emitir('decidir', item.recommendation_instance_id, 'approved')"
      >
        Estuvo bien
      </BotonAccion>

      <BotonAccion
        tono="negativo"
        class="tarjeta__boton tarjeta__boton--mal"
        :disabled="enviando"
        @click="emitir('decidir', item.recommendation_instance_id, 'rejected')"
      >
        No estuvo bien
      </BotonAccion>
    </div>
  </article>
</template>

<style scoped>
.tarjeta {
  --blubathon-avatar: 30px;

  display: flex;
  flex-direction: column;
  gap: var(--blubathon-esp-10);
  padding: var(--blubathon-esp-16);
  background:
    radial-gradient(90% 150% at 0% 0%, var(--blubathon-rec-tinte), transparent 58%),
    var(--blubathon-superficie);
  border-radius: var(--blubathon-radio-18);
  box-shadow: var(--blubathon-elev-1);
}

.tarjeta__cabecera {
  display: flex;
  gap: var(--blubathon-esp-10);
  align-items: center;
}

.tarjeta__quien {
  flex: 1;
  min-width: 0;
}

.tarjeta__nombre {
  overflow: hidden;
  font-size: var(--blubathon-fs-15);
  font-weight: 700;
  color: var(--blubathon-marca-titulo);
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* La banda dicha con palabras y con cifra. El color la refuerza; quien no lo
   distingue lee lo mismo. */
.tarjeta__estado {
  font-size: var(--blubathon-fs-12);
  font-weight: 600;
  color: var(--blubathon-texto-suave, var(--blubathon-gris-texto));
  font-variant-numeric: tabular-nums;
}

.tarjeta__perfil {
  flex: none;
  padding: var(--blubathon-esp-6) var(--blubathon-esp-10);
  font-size: var(--blubathon-fs-12);
  font-weight: 700;
  color: var(--blubathon-marca-accion);
  background: var(--blubathon-vidrio);
  border-radius: var(--blubathon-radio-pastilla);
}

.tarjeta__perfil:hover {
  background: var(--blubathon-marca-icono-fondo);
}

.tarjeta__perfil:focus-visible,
.tarjeta__mas:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-marca-accion);
  outline-offset: var(--blubathon-foco-offset);
}

.tarjeta__texto {
  font-size: var(--blubathon-fs-135);
  line-height: 1.5;
  color: var(--blubathon-marca-texto);
}

/*
 * Tres renglones y el resto detrás del "Leer más". Una recomendación larga en
 * una cola de cinco convierte el widget en una pantalla de lectura, y lo que se
 * hace aquí es comparar y responder, no leer de corrido.
 */
.tarjeta__texto--recortado {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  overflow: hidden;
}

.tarjeta__proposito {
  font-size: var(--blubathon-fs-13);
  line-height: 1.45;
  color: var(--blubathon-gris-texto);
}

.tarjeta__mas {
  display: inline-flex;
  gap: var(--blubathon-esp-6);
  align-self: flex-start;
  align-items: center;
  font-size: var(--blubathon-fs-125);
  font-weight: 700;
  color: var(--blubathon-marca-accion);
}

.tarjeta__mas:hover {
  text-decoration: underline;
}

.tarjeta__flecha {
  width: var(--blubathon-icono-14);
  height: var(--blubathon-icono-14);
  transform: scaleX(-1);
}

.tarjeta__flecha--atras {
  transform: rotate(90deg);
}

.citas {
  display: flex;
  flex-direction: column;
  gap: var(--blubathon-esp-8);
}

.citas__cita {
  padding-left: var(--blubathon-esp-10);
  border-left: 2px solid var(--blubathon-linea);
}

.citas__texto {
  font-size: var(--blubathon-fs-12);
  font-style: italic;
  line-height: 1.45;
  color: var(--blubathon-marca-texto);
}

.citas__fuente {
  margin-top: 2px;
  font-size: var(--blubathon-fs-11);
  color: var(--blubathon-gris-texto);
}

.veredicto {
  padding: var(--blubathon-esp-8) var(--blubathon-esp-12);
  font-size: var(--blubathon-fs-12);
  font-weight: 700;
  text-align: center;
  border-radius: var(--blubathon-radio-10);
}

.veredicto--approved {
  color: var(--blubathon-exito-texto);
  background: var(--blubathon-exito-fondo);
}

.veredicto--rejected {
  color: var(--blubathon-alerta-texto);
  background: var(--blubathon-alerta-fondo);
}

.tarjeta__acciones {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--blubathon-esp-10);
}

@media (max-width: 480px) {
  .tarjeta__acciones {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
