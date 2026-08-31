/**
 * El estado del panel del terapeuta: la cartera de niños y la cola de revisión.
 *
 * Dos cargas independientes y no una: la cola de revisión atraviesa a todos los
 * niños y no depende de cuál esté seleccionado, así que revisar una
 * recomendación no tiene por qué volver a pedir seis historiales, y elegir otro
 * niño no tiene por qué recargar la cola.
 *
 * Estado de módulo, como `estado/nino.ts`: el panel, el perfil y el widget del
 * conjunto miran la misma cartera y ninguno debería volver a pedirla.
 */

import { computed, ref } from "vue";

import { colaDeRevision, historialNino, listarNinos, obtenerNino } from "@/api/blubathon";
import { DIAS_HISTORIAL } from "@/api/config";
import type { ReviewQueueResponse } from "@/api/contrato";
import { mensajeDeError } from "@/api/cliente";
import { resumirConjunto } from "@/dominio/conjunto";
import {
  adherencia,
  pendientesDeCierre,
  serieRiesgo,
  tasaObservada,
  ultimoRiesgo,
} from "@/dominio/serieRiesgo";
import type { FichaNino } from "@/types/terapeuta";

const fichas = ref<FichaNino[]>([]);
const cargandoCartera = ref(false);
const errorCartera = ref<string | null>(null);

const cola = ref<ReviewQueueResponse | null>(null);
const cargandoCola = ref(false);
const errorCola = ref<string | null>(null);

/** A quién se está mirando. `null` mientras no haya cartera. */
const seleccionado = ref<string | null>(null);

let carteraEnCurso: Promise<void> | null = null;

/**
 * Arma la ficha de un niño con las dos llamadas que la componen.
 *
 * Se piden en paralelo: son independientes, y encadenarlas multiplicaría por
 * dos la espera de una pantalla que ya está pidiendo seis fichas a la vez.
 */
async function ficha(id: string, etiqueta: string): Promise<FichaNino> {
  const [perfil, historial] = await Promise.all([
    obtenerNino(id),
    historialNino(id, { limite: DIAS_HISTORIAL }),
  ]);
  const dias = historial.days ?? [];
  const serie = serieRiesgo(dias);

  return {
    id,
    // La etiqueta de la lista y la del perfil son la misma, pero la de la lista
    // llega antes: se usa esa y no la del perfil para que la columna no cambie
    // de texto cuando terminan de resolverse las fichas.
    etiqueta: etiqueta || perfil.display_label,
    riesgo: ultimoRiesgo(serie),
    serie,
    tasa: tasaObservada(serie),
    adherencia: adherencia(serie),
    pendientes: pendientesDeCierre(dias),
    perfilSensorial: perfil.sensory_profile_tags ?? [],
    apoyosComunicacion: perfil.communication_support_tags ?? [],
    contraindicaciones: perfil.contraindication_tags ?? [],
  };
}

async function pedirCartera(): Promise<void> {
  cargandoCartera.value = true;
  errorCartera.value = null;
  try {
    const lista = (await listarNinos()).children ?? [];
    // `allSettled` y no `all`: un niño cuyo historial falle no puede dejar la
    // pantalla entera en blanco. El resto de la cartera es información válida.
    const resueltas = await Promise.allSettled(
      lista.map((nino) => ficha(nino.child_id, nino.display_label)),
    );
    fichas.value = resueltas
      .filter((resultado) => resultado.status === "fulfilled")
      .map((resultado) => resultado.value);

    if (resueltas.some((resultado) => resultado.status === "rejected")) {
      errorCartera.value = "Algunas fichas no se pudieron cargar.";
    }
    if (seleccionado.value === null || !fichas.value.some((f) => f.id === seleccionado.value)) {
      seleccionado.value = fichas.value[0]?.id ?? null;
    }
  } catch (fallo) {
    errorCartera.value = mensajeDeError(fallo);
  } finally {
    cargandoCartera.value = false;
  }
}

async function pedirCola(): Promise<void> {
  cargandoCola.value = true;
  errorCola.value = null;
  try {
    cola.value = await colaDeRevision();
  } catch (fallo) {
    errorCola.value = mensajeDeError(fallo);
  } finally {
    cargandoCola.value = false;
  }
}

/** Vacía la cartera y la cola. Solo lo usan las pruebas: el estado es de módulo. */
export function olvidarTerapeuta(): void {
  fichas.value = [];
  cargandoCartera.value = false;
  errorCartera.value = null;
  cola.value = null;
  cargandoCola.value = false;
  errorCola.value = null;
  seleccionado.value = null;
  carteraEnCurso = null;
}

export function useTerapeuta() {
  /**
   * Pide la cartera. Las llamadas que coincidan mientras una está en vuelo
   * comparten esa misma promesa: el panel monta cuatro piezas y todas la
   * necesitan, y sin esto serían cuatro tandas de seis historiales cada una.
   */
  function cargarCartera(forzar = false): Promise<void> {
    if (forzar) return pedirCartera();
    carteraEnCurso ??= pedirCartera().finally(() => {
      carteraEnCurso = null;
    });
    return carteraEnCurso;
  }

  function seleccionar(id: string): void {
    seleccionado.value = id;
  }

  return {
    fichas,
    cargandoCartera,
    errorCartera,
    cargarCartera,

    cola,
    cargandoCola,
    errorCola,
    cargarCola: pedirCola,

    seleccionado,
    seleccionar,
    ficha: computed(() => fichas.value.find((f) => f.id === seleccionado.value) ?? null),
    conjunto: computed(() => resumirConjunto(fichas.value)),
  };
}
