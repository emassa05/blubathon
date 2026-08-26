/**
 * A quién estamos acompañando.
 *
 * La API v0.4 tiene el tenant fijo y no pide sesión: la lista de
 * `GET /v1/children` es todo lo que hace falta para saber de quién son los
 * datos. La demo trae una sola persona, así que se toma la primera; si algún
 * día vinieran varias, este es el único sitio que hay que tocar.
 *
 * Es estado de módulo y no un `provide`: la pantalla de Salud, el historial y
 * el diálogo del cuestionario necesitan el mismo `child_id` y ninguno debería
 * volver a pedirlo.
 */

import { computed, ref } from "vue";

import { ID_NINO } from "@/api/config";
import type { ChildListItem } from "@/api/contrato";
import { mensajeDeError } from "@/api/cliente";
import { listarNinos } from "@/api/faro";

const nino = ref<ChildListItem | null>(null);
const cargando = ref(false);
const error = ref<string | null>(null);
let enCurso: Promise<void> | null = null;

async function pedir(): Promise<void> {
  cargando.value = true;
  error.value = null;
  try {
    const lista = (await listarNinos()).children ?? [];
    nino.value = lista.find((candidato) => candidato.child_id === ID_NINO) ?? lista[0] ?? null;
  } catch (fallo) {
    error.value = mensajeDeError(fallo);
  } finally {
    cargando.value = false;
  }
}

export function useNino() {
  /** Pide la lista una sola vez por sesión, aunque la llamen varias pantallas. */
  function cargar(): Promise<void> {
    enCurso ??= pedir().finally(() => {
      enCurso = null;
    });
    return enCurso;
  }

  return {
    nino,
    ninoId: computed(() => nino.value?.child_id ?? null),
    etiqueta: computed(() => nino.value?.display_label ?? ""),
    cargando,
    error,
    cargar,
  };
}
