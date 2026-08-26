/**
 * El cuestionario de un día: qué se pregunta, qué se ha contestado y qué se
 * envía.
 *
 * Dos llamadas, las dos que ya existen:
 *
 * - `POST /children/{id}/form-plan` da el plan sin estado: qué campos destacar
 *   hoy, por qué, qué sugerencias hay y cuánta cobertura tiene el historial.
 *   No abre ninguna sesión ni escribe nada, así que pedirlo es gratis.
 * - `POST /children/{id}/forms` envía el día entero de una vez.
 *
 * Lo que el borrador respeta del contrato, porque es contrato y no estilo:
 *
 * - Una sugerencia se enseña como ayuda y **nunca** como valor precargado del
 *   control. Aceptarla es un acto explícito, y solo entonces la respuesta viaja
 *   como `accept_default`; tocarla después la convierte en `edit_default`.
 * - "No sé" es una respuesta, distinta de dejar el campo vacío: viaja como
 *   `unknown` y el servidor la registra sin valor.
 */

import { computed, ref } from "vue";

import type {
  AnswerItem,
  DefaultSuggestion,
  FieldCode,
  FormPlanResponse,
  FormQuestion,
  FormSubmissionResponse,
  Interaccion,
  ValorCampo,
} from "@/api/contrato";
import { ORIGEN_CUIDADOR } from "@/api/contrato";
import { mensajeDeError } from "@/api/cliente";
import { enviarFormulario, planDelFormulario } from "@/api/faro";
import { CAMPOS_DE_CASA, ordenCanonico } from "@/dominio/campos";
import { variablesCriticas, type DiaConRespuestas } from "@/dominio/criticas";

export interface Borrador {
  readonly valor?: ValorCampo;
  readonly interaccion: Interaccion;
}

export type Borradores = Partial<Record<FieldCode, Borrador>>;

interface Opciones {
  readonly ninoId: string;
  readonly fecha: string;
  /** Respuestas ya guardadas de ese día, si el cuestionario se abre otra vez. */
  readonly previas?: Readonly<Partial<Record<FieldCode, ValorCampo>>>;
  /** Días anteriores con respuestas, para comparar contra lo habitual. */
  readonly anteriores?: readonly DiaConRespuestas[];
}

export function useCuestionario(opciones: Opciones) {
  const plan = ref<FormPlanResponse | null>(null);
  const cargando = ref(false);
  const error = ref<string | null>(null);
  const enviando = ref(false);
  const errorEnvio = ref<string | null>(null);
  const resultado = ref<FormSubmissionResponse | null>(null);
  const borradores = ref<Borradores>({});

  // Reabrir un día ya enviado no empieza de cero: lo contestado se recupera de
  // la copia local, porque la API no devuelve las respuestas de un envío.
  for (const [clave, valor] of Object.entries(opciones.previas ?? {})) {
    if (valor === undefined) continue;
    borradores.value[clave as FieldCode] = { valor, interaccion: "manual" };
  }

  const yaEnviado = Object.keys(opciones.previas ?? {}).length > 0;

  /** Lo contestado, en la forma que pide el plan: campo → valor. */
  const respondidas = computed<Partial<Record<FieldCode, ValorCampo>>>(() => {
    const registro: Partial<Record<FieldCode, ValorCampo>> = {};
    for (const [clave, borrador] of Object.entries(borradores.value)) {
      if (borrador?.valor !== undefined) registro[clave as FieldCode] = borrador.valor;
    }
    return registro;
  });

  /**
   * Las preguntas del día.
   *
   * El plan manda en el orden: primero lo que destaca y en el orden en que lo
   * devuelve. Si el plan no llegó —la API está apagada—, el cuestionario sigue
   * en pie con el orden canónico del catálogo, que es del contrato y no de la
   * red.
   */
  const preguntas = computed<readonly FormQuestion[]>(() => {
    const delPlan = plan.value?.questions ?? [];
    if (delPlan.length > 0) return delPlan;
    return CAMPOS_DE_CASA.map((campo) => ({
      field_code: campo,
      highlighted: false,
      reason: "canonical_order" as const,
      voi_nats: null,
    }));
  });

  const destacadas = computed(() => preguntas.value.filter((pregunta) => pregunta.highlighted));
  const resto = computed(() =>
    [...preguntas.value.filter((pregunta) => !pregunta.highlighted)].sort(
      (uno, otro) => ordenCanonico(uno.field_code) - ordenCanonico(otro.field_code),
    ),
  );

  const sugerencias = computed(() => {
    const indice = new Map<FieldCode, DefaultSuggestion>();
    for (const sugerencia of plan.value?.defaults ?? []) {
      indice.set(sugerencia.field_code, sugerencia);
    }
    return indice;
  });

  const contestadas = computed(
    () => Object.values(borradores.value).filter((borrador) => borrador !== undefined).length,
  );

  const criticas = computed(() =>
    variablesCriticas(respondidas.value, opciones.fecha, opciones.anteriores ?? []),
  );

  async function cargarPlan(): Promise<void> {
    cargando.value = true;
    error.value = null;
    try {
      plan.value = await planDelFormulario(opciones.ninoId, respondidas.value);
    } catch (fallo) {
      error.value = mensajeDeError(fallo);
    } finally {
      cargando.value = false;
    }
  }

  function responder(campo: FieldCode, valor: ValorCampo, interaccion: Interaccion): void {
    borradores.value = { ...borradores.value, [campo]: { valor, interaccion } };
  }

  /** "No sé": se registra como respuesta, sin valor. */
  function noSabe(campo: FieldCode): void {
    borradores.value = { ...borradores.value, [campo]: { interaccion: "unknown" } };
  }

  function borrar(campo: FieldCode): void {
    const copia = { ...borradores.value };
    delete copia[campo];
    borradores.value = copia;
  }

  async function enviar(): Promise<FormSubmissionResponse | null> {
    enviando.value = true;
    errorEnvio.value = null;
    try {
      const respuesta = await enviarFormulario(opciones.ninoId, {
        source: ORIGEN_CUIDADOR,
        local_date: opciones.fecha,
        answers: Object.entries(borradores.value).flatMap(([clave, borrador]) => {
          if (borrador === undefined) return [];
          const respuestaCampo: AnswerItem = {
            field_code: clave as FieldCode,
            interaction: borrador.interaccion,
          };
          const valorEnviado = borrador.valor;
          if (valorEnviado !== undefined) {
            // El contrato pide un array mutable; el borrador lo guarda de solo
            // lectura para que nadie lo modifique por debajo.
            respuestaCampo.value =
              typeof valorEnviado === "object" ? [...valorEnviado] : valorEnviado;
          }
          return [respuestaCampo];
        }),
      });
      resultado.value = respuesta;
      return respuesta;
    } catch (fallo) {
      errorEnvio.value = mensajeDeError(fallo);
      return null;
    } finally {
      enviando.value = false;
    }
  }

  return {
    plan,
    cargando,
    error,
    enviando,
    errorEnvio,
    resultado,
    borradores,
    respondidas,
    preguntas,
    destacadas,
    resto,
    sugerencias,
    contestadas,
    criticas,
    yaEnviado,
    cargarPlan,
    responder,
    noSabe,
    borrar,
    enviar,
  };
}
