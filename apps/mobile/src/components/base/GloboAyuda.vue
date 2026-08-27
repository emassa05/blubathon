<script setup lang="ts">
/**
 * El globo de ayuda: un "(?)" y una explicación corta debajo.
 *
 * No es un diálogo y la diferencia importa. El diálogo de desregulación exige
 * una respuesta y para eso tapa la pantalla; esto no exige nada, así que no
 * lleva velo, no atrapa el foco, no bloquea nada de lo que hay detrás y se
 * cierra por donde quiera: el mismo botón, `Esc`, o pulsando fuera.
 *
 * Se coloca en `position: fixed` y con la posición medida al abrir, no con un
 * `absolute` colgado del disparador. La razón es que el "(?)" está donde esté:
 * en la cabecera del cuestionario cae pegado al borde izquierdo y en la del
 * riesgo va centrado, y un globo de 268 px anclado a la izquierda del segundo se
 * salía por el borde derecho de la pantalla. Un `max-width` no lo arregla —topa
 * el ancho, no el sitio—, así que se mide el disparador y se topa la posición
 * contra la ventana.
 *
 * Sigue sin `Teleport`: se declara donde se usa y las pruebas lo encuentran ahí.
 */
import { nextTick, onBeforeUnmount, ref, useId, watch, type CSSProperties } from "vue";

import IconoCerrar from "@/components/icons/IconoCerrar.vue";
import IconoInfo from "@/components/icons/IconoInfo.vue";

const props = withDefaults(
  defineProps<{
    /** Nombre del botón para quien no ve el glifo. */
    etiqueta: string;
    titulo: string;
    /** De qué lado del ancla se abre. En móvil siempre cae dentro. */
    lado?: "izquierda" | "derecha";
    /** El glifo hereda el color del contexto salvo que se diga otra cosa. */
    tono?: "panel" | "tarjeta";
  }>(),
  { lado: "derecha", tono: "tarjeta" },
);

const abierto = ref(false);
const ancla = ref<HTMLElement | null>(null);
const globo = ref<HTMLElement | null>(null);
const disparador = ref<HTMLElement | null>(null);
const idGlobo = useId();

/** Lo que se deja libre entre el globo y el borde de la ventana. */
const MARGEN = 12;

const sitio = ref<CSSProperties>({});

/**
 * Coloca el globo debajo del disparador y dentro de la ventana.
 *
 * Se prefiere el lado que pide la prop, y si por ahí no cabe se topa contra el
 * borde: nunca se recorta ni se sale, sea cual sea la posición del "(?)".
 */
function colocar(): void {
  const boton = disparador.value?.getBoundingClientRect();
  const caja = globo.value?.getBoundingClientRect();
  if (boton === undefined || caja === undefined) return;

  const preferido = props.lado === "derecha" ? boton.left - 6 : boton.right + 6 - caja.width;
  const tope = Math.max(MARGEN, window.innerWidth - caja.width - MARGEN);

  sitio.value = {
    left: `${Math.round(Math.min(tope, Math.max(MARGEN, preferido)))}px`,
    top: `${Math.round(boton.bottom - 4)}px`,
  };
}

function alternar(): void {
  abierto.value = !abierto.value;
}

function cerrar(): void {
  abierto.value = false;
}

/* Fuera del globo y fuera del botón: cerrar. Dentro, no —seleccionar el texto
   de la explicación no puede hacerla desaparecer. */
function alPulsarFuera(evento: MouseEvent): void {
  const donde = evento.target as Node | null;
  if (donde === null) return;
  if (ancla.value?.contains(donde) === true) return;
  cerrar();
}

function alTeclear(evento: KeyboardEvent): void {
  if (evento.key !== "Escape") return;
  // No se propaga: dentro del cuestionario, `Esc` con el globo abierto cierra
  // el globo y deja el diálogo donde estaba. Cerrar los dos de una tecla
  // perdería el formulario a medio contestar.
  evento.stopPropagation();
  cerrar();
}

watch(abierto, async (visible) => {
  if (!visible) {
    document.removeEventListener("pointerdown", alPulsarFuera);
    document.removeEventListener("keydown", alTeclear, true);
    return;
  }
  document.addEventListener("pointerdown", alPulsarFuera);
  document.addEventListener("keydown", alTeclear, true);
  // El foco entra en el globo para que un lector lo lea al abrirlo. No queda
  // atrapado: tabular sale del globo y sigue por el formulario.
  await nextTick();
  colocar();
  globo.value?.focus();
});

/* Desplazar o redimensionar mueve el disparador: el globo lo sigue en vez de
   quedarse flotando donde estaba. */
watch(abierto, (visible) => {
  const metodo = visible ? "addEventListener" : "removeEventListener";
  window[metodo]("resize", colocar);
  window[metodo]("scroll", colocar, true);
});

onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", alPulsarFuera);
  document.removeEventListener("keydown", alTeclear, true);
  window.removeEventListener("resize", colocar);
  window.removeEventListener("scroll", colocar, true);
});
</script>

<template>
  <span ref="ancla" class="ayuda" :class="`ayuda--${tono}`">
    <button
      ref="disparador"
      type="button"
      class="ayuda__disparador"
      :aria-label="etiqueta"
      :aria-expanded="abierto"
      :aria-controls="idGlobo"
      @click="alternar"
    >
      <IconoInfo class="ayuda__glifo" />
    </button>

    <!-- Corta y en el sitio: entra con una opacidad y un desplazamiento de 4px,
         que orienta de dónde salió sin que haya que esperar a que llegue. -->
    <Transition name="globo">
      <span
        v-if="abierto"
        :id="idGlobo"
        ref="globo"
        class="ayuda__globo"
        :style="sitio"
        role="dialog"
        :aria-label="titulo"
        tabindex="-1"
      >
        <span class="ayuda__cabecera">
          <span class="ayuda__titulo">{{ titulo }}</span>
          <button
            type="button"
            class="ayuda__cerrar"
            aria-label="Cerrar la explicación"
            @click="cerrar"
          >
            <IconoCerrar class="ayuda__aspa" />
          </button>
        </span>

        <span class="ayuda__cuerpo"><slot /></span>
      </span>
    </Transition>
  </span>
</template>

<style scoped>
.ayuda {
  position: relative;
  display: inline-flex;
  vertical-align: middle;
}

/*
 * 44x44 de área táctil que ocupa en la línea lo que su glifo: los márgenes
 * negativos devuelven lo que el acolchado le robaría al texto de al lado. Es la
 * misma cuenta que ya hacía el botón de información de la cabecera del riesgo.
 */
.ayuda__disparador {
  display: grid;
  flex: none;
  place-items: center;
  min-width: var(--blubathon-toque);
  min-height: var(--blubathon-toque);
  margin-block: calc((var(--blubathon-toque) - var(--blubathon-icono-16)) / -2);
  margin-inline: calc(
      var(--blubathon-esp-6) - (var(--blubathon-toque) - var(--blubathon-icono-16)) / 2
    )
    calc((var(--blubathon-toque) - var(--blubathon-icono-16)) / -2);
  color: inherit;
  border-radius: var(--blubathon-radio-10);
}

.ayuda--panel .ayuda__disparador {
  color: var(--blubathon-texto-suave);
}

.ayuda--tarjeta .ayuda__disparador {
  color: var(--blubathon-marca-accion);
}

.ayuda--panel .ayuda__disparador:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-foco-panel);
  outline-offset: var(--blubathon-foco-offset);
}

.ayuda--tarjeta .ayuda__disparador:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-foco-oscuro);
  outline-offset: var(--blubathon-foco-offset);
}

.ayuda__glifo {
  width: var(--blubathon-icono-16);
  height: var(--blubathon-icono-16);
}

/*
 * El globo. Es una tarjeta del sistema —superficie, radio 14— con la elevación
 * del diálogo, porque flota sobre el contenido y no con él.
 *
 * El ancho se topa con `min()` contra el hueco de la ventana: en un teléfono de
 * 320 no se sale por el lado, y en cualquier pantalla mayor se queda en 268 en
 * vez de estirarse hasta dejar una línea de dos palabras.
 */
.ayuda__globo {
  position: fixed;
  /* Fuera de la ventana hasta que `colocar` lo mide: sin esto asoma en la
     esquina durante el primer fotograma. */
  top: -9999px;
  left: -9999px;
  z-index: 40;
  display: flex;
  flex-direction: column;
  gap: var(--blubathon-esp-6);
  width: max-content;
  max-width: min(268px, calc(100vw - var(--blubathon-esp-24)));
  padding: var(--blubathon-esp-12) var(--blubathon-esp-14);
  text-align: left;
  text-transform: none;
  letter-spacing: normal;
  background: var(--blubathon-superficie);
  border-radius: var(--blubathon-radio-14);
  box-shadow: var(--blubathon-elev-dialogo);
}

.ayuda__globo:focus-visible {
  outline: none;
}

.ayuda__cabecera {
  display: flex;
  align-items: flex-start;
  gap: var(--blubathon-esp-8);
}

.ayuda__titulo {
  flex: 1;
  font-size: var(--blubathon-fs-135);
  font-weight: 700;
  line-height: 1.35;
  color: var(--blubathon-marca-profundo);
}

/*
 * El aspa es pequeña a propósito: el globo se cierra de cuatro maneras y esta es
 * la menos probable. Sigue midiendo 24 de área, que es lo que pide un control
 * secundario dentro de otro control ya alcanzado con el dedo.
 */
.ayuda__cerrar {
  display: grid;
  flex: none;
  place-items: center;
  width: var(--blubathon-esp-24);
  height: var(--blubathon-esp-24);
  margin: calc(var(--blubathon-esp-4) * -1) calc(var(--blubathon-esp-4) * -1) 0 0;
  color: var(--blubathon-gris-texto);
  border-radius: 50%;
}

.ayuda__cerrar:hover {
  background: var(--blubathon-fila-activa);
}

.ayuda__cerrar:focus-visible {
  outline: var(--blubathon-foco-grosor) solid var(--blubathon-foco-oscuro);
  outline-offset: 1px;
}

.ayuda__aspa {
  width: var(--blubathon-icono-12);
  height: var(--blubathon-icono-12);
}

.ayuda__cuerpo {
  font-size: var(--blubathon-fs-125);
  font-weight: 400;
  line-height: 1.5;
  color: var(--blubathon-marca-texto);
}

.ayuda__cuerpo :deep(p + p) {
  margin-top: var(--blubathon-esp-8);
}

/* 140ms: lo justo para que no parpadee. Un globo de ayuda que se hace esperar
   es peor que uno que aparece puesto. */
.globo-enter-active,
.globo-leave-active {
  transition:
    opacity 140ms ease-out,
    transform 140ms ease-out;
}

.globo-enter-from,
.globo-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

@media (prefers-reduced-motion: reduce) {
  .globo-enter-active,
  .globo-leave-active {
    transition: opacity 140ms ease-out;
  }

  .globo-enter-from,
  .globo-leave-to {
    transform: none;
  }
}
</style>
