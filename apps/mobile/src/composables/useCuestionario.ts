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
 *
 * Aparte de eso, los campos numéricos no nacen vacíos: salen en 1. Es un valor
 * de salida de la pantalla, no una sugerencia del servidor, y por eso no se
 * enseña como tal ni suprime la sugerencia de su propio campo —ver `sembrados`.
 */

import { computed, ref, watch } from "vue";

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
import { enviarFormulario, planFormulario } from "@/api/blubathon";
import {
  CAMPOS_DE_CASA,
  esNumerico,
  especificacionCampo,
  ordenCanonico,
  valorInicialNumerico,
} from "@/dominio/campos";

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
}

export function useCuestionario(opciones: Opciones) {
  const plan = ref<FormPlanResponse | null>(null);
  const cargando = ref(false);
  const error = ref<string | null>(null);
  const enviando = ref(false);
  const errorEnvio = ref<string | null>(null);
  const resultado = ref<FormSubmissionResponse | null>(null);
  const borradores = ref<Borradores>({});

  /*
   * Los campos numéricos que nacieron con su valor de salida y que nadie ha
   * tocado todavía.
   *
   * Hay que saber cuáles son por dos motivos, y los dos son de no afirmar algo
   * que nadie dijo:
   *
   * - **No suprimen la sugerencia.** El plan usa `answers` para no volver a
   *   proponer un valor de un campo que ya está contestado (SPEC 6.6). Un 1 que
   *   puso la pantalla no lo contestó nadie, y dejarlo viajar ahí borraría la
   *   sugerencia de ese mismo campo.
   * - **No sobreviven a una pregunta que no se llega a hacer.** Si el plan
   *   acaba pidiendo menos campos de los que había sembrados, los que se caen
   *   salen del borrador: nadie los vio y no pueden ir en el envío.
   *
   * En cuanto se toca uno deja de estar aquí y pasa a ser una respuesta como
   * cualquier otra, que sí cuenta y sí se envía.
   */
  const sembrados = new Set<FieldCode>();

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
   * Lo que ha contestado quien responde, sin los valores de salida que todavía
   * no ha tocado nadie. Es lo que ve el plan; el envío ve `respondidas`.
   */
  function declaradas(): Partial<Record<FieldCode, ValorCampo>> {
    const registro = { ...respondidas.value };
    for (const campo of sembrados) delete registro[campo];
    return registro;
  }

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

  /**
   * Las preguntas en el orden en que se hacen: primero lo que el plan destaca y
   * después el resto, en orden canónico. Es el mismo orden que ya tenía el
   * cuestionario cuando iba de corrido; lo único que cambia es que ahora se
   * recorre de tres en tres.
   */
  const enOrden = computed<readonly FormQuestion[]>(() => [...destacadas.value, ...resto.value]);

  /*
   * El valor de salida de los campos numéricos.
   *
   * Se siembra en cuanto se sabe qué se pregunta —al montar, con el catálogo, y
   * otra vez cuando llega el plan— y solo sobre lo que está sin contestar: un
   * día que se reabre conserva lo suyo.
   */
  function sembrarNumericos(campos: readonly FieldCode[]): void {
    const pedidos = new Set(campos);
    const copia = { ...borradores.value };
    let cambio = false;

    for (const campo of [...sembrados]) {
      if (pedidos.has(campo)) continue;
      sembrados.delete(campo);
      delete copia[campo];
      cambio = true;
    }

    for (const campo of campos) {
      if (copia[campo] !== undefined) continue;
      const especificacion = especificacionCampo(campo);
      if (especificacion === undefined || !esNumerico(especificacion)) continue;
      copia[campo] = { valor: valorInicialNumerico(especificacion), interaccion: "manual" };
      sembrados.add(campo);
      cambio = true;
    }

    if (cambio) borradores.value = copia;
  }

  watch(preguntas, (lista) => sembrarNumericos(lista.map((pregunta) => pregunta.field_code)), {
    immediate: true,
  });

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

  async function cargarPlan(): Promise<void> {
    cargando.value = true;
    error.value = null;
    try {
      plan.value = await planFormulario(opciones.ninoId, {
        source: ORIGEN_CUIDADOR,
        answers: declaradas(),
      });
    } catch (fallo) {
      error.value = mensajeDeError(fallo);
    } finally {
      cargando.value = false;
    }
  }

  function responder(campo: FieldCode, valor: ValorCampo, interaccion: Interaccion): void {
    sembrados.delete(campo);
    borradores.value = { ...borradores.value, [campo]: { valor, interaccion } };
  }

  /** "No sé": se registra como respuesta, sin valor. */
  function noSabe(campo: FieldCode): void {
    sembrados.delete(campo);
    borradores.value = { ...borradores.value, [campo]: { interaccion: "unknown" } };
  }

  function borrar(campo: FieldCode): void {
    sembrados.delete(campo);
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
    enOrden,
    sugerencias,
    contestadas,
    yaEnviado,
    cargarPlan,
    responder,
    noSabe,
    borrar,
    enviar,
  };
}
