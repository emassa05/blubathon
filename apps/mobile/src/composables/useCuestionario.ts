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
 * - Una sugerencia **nunca** es un valor precargado del control: el campo sigue
 *   vacío hasta que se decide algo sobre él, y aceptarla es un acto explícito
 *   que viaja como `accept_default`; tocarla después la convierte en
 *   `edit_default`.
 *
 *   Lo que cambió es **cuándo** se decide. Antes cada sugerencia se enseñaba en
 *   su campo con un botón "usar esta respuesta", y dieciocho preguntas con su
 *   propia caja de ayuda hacían el formulario más largo justo donde intentaba
 *   ser más corto. Ahora las sugerencias no se ven mientras se contesta y la
 *   decisión se toma una sola vez, al final, sobre la lista de las que quedaron
 *   sin tocar: revisarlas una a una, o aceptarlas todas. Aceptarlas todas es lo
 *   que hace `aplicarSugerencias`, y viaja exactamente igual que viajaba el
 *   botón de cada campo —mismo `accept_default`, mismo cuerpo de envío.
 * El contrato admite además una respuesta `unknown` —contestar "no sé" sin dar
 * valor—, pero el cuestionario ya no la ofrece: era una salida a un dedo de
 * distancia de cada pregunta, y una pregunta sin contestar y un "no sé" acaban
 * pesando lo mismo en la estimación. Lo que no se sabe se deja en blanco, que
 * es lo que el formulario ya permitía.
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
  sePregunta,
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

  const sembrados = new Set<FieldCode>();

  /**
   * Los campos sobre los que quien responde ha decidido algo: los que ha tocado
   * a mano y los que ha aceptado desde la revisión.
   *
   * Es lo que separa "contestado" de "tiene un valor en el borrador". Un campo
   * numérico nace en 1 sin que nadie lo haya mirado, y si además tiene
   * sugerencia esa sugerencia sigue pendiente: el 1 es un valor de salida de la
   * pantalla, no una respuesta.
   */
  const tocados = ref(new Set<FieldCode>());

  /** Los campos cuya sugerencia se enseña porque se pidió revisarla. */
  const revelados = ref(new Set<FieldCode>());

  // Reabrir un día ya enviado no empieza de cero: lo contestado se recupera de
  // la copia local, porque la API no devuelve las respuestas de un envío.
  for (const [clave, valor] of Object.entries(opciones.previas ?? {})) {
    if (valor === undefined) continue;
    borradores.value[clave as FieldCode] = { valor, interaccion: "manual" };
    // Un día que se reabre trae respuestas de verdad: no vuelven a contar como
    // sugerencias pendientes de decidir.
    tocados.value.add(clave as FieldCode);
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
    // El plan devuelve el catálogo entero, incluidos los campos que el
    // cuestionario ya no pregunta: se filtran aquí, que es por donde pasan los
    // dos caminos —el del plan y el del catálogo— antes de contarse en páginas.
    const delPlan = (plan.value?.questions ?? []).filter((pregunta) =>
      sePregunta(pregunta.field_code),
    );
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

  const sugerencias = computed(() => {
    const indice = new Map<FieldCode, DefaultSuggestion>();
    for (const sugerencia of plan.value?.defaults ?? []) {
      indice.set(sugerencia.field_code, sugerencia);
    }
    return indice;
  });

  /**
   * Lo que el formulario pregunta de verdad: `enOrden` menos lo que ya se sabe.
   *
   * El plan devuelve dos cosas y no son la misma lista. `questions` es todo lo
   * que se **puede** preguntar; `defaults` es lo que Blubathon ya aprendió de
   * los últimos dos meses porque se responde casi siempre igual. Preguntar lo
   * segundo es preguntar lo que ya se sabe: alarga el formulario justo con los
   * campos donde la respuesta era previsible, y deja la revisión del final sin
   * nada que revisar salvo lo que se acaba de contestar a mano.
   *
   * Así que lo aprendido no se pregunta. Sale al final, en la revisión, como lo
   * que Blubathon va a enviar por ti, con la opción de cambiarlo.
   *
   * Se mira la sugerencia y no si se ha tocado, para que el conjunto de
   * preguntas no cambie a media sesión: si dependiera de lo contestado, aceptar
   * o editar algo repaginaría el formulario por debajo.
   */
  const aPreguntar = computed<readonly FormQuestion[]>(() =>
    enOrden.value.filter((pregunta) => !sugerencias.value.has(pregunta.field_code)),
  );

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

  watch(aPreguntar, (lista) => sembrarNumericos(lista.map((pregunta) => pregunta.field_code)), {
    immediate: true,
  });

  const contestadas = computed(
    () => Object.values(borradores.value).filter((borrador) => borrador !== undefined).length,
  );

  /**
   * Las sugerencias que siguen sin decidirse: hay una para ese campo y nadie lo
   * ha tocado.
   *
   * En el orden en que se pregunta, no en el que las devuelve el plan: la lista
   * de revisión se lee junto al formulario que se acaba de contestar, y dos
   * órdenes distintos para las mismas preguntas obligarían a buscar cada una.
   */
  const sugerenciasPendientes = computed<readonly DefaultSuggestion[]>(() =>
    enOrden.value.flatMap((pregunta) => {
      if (tocados.value.has(pregunta.field_code)) return [];
      const sugerencia = sugerencias.value.get(pregunta.field_code);
      return sugerencia === undefined ? [] : [sugerencia];
    }),
  );

  /** ¿Se enseña la sugerencia de este campo? Solo si se pidió revisarla. */
  function sugerenciaVisible(campo: FieldCode): boolean {
    return revelados.value.has(campo);
  }

  /**
   * Acepta de una vez las sugerencias que quedaron sin tocar.
   *
   * Es lo mismo que pulsar "usar esta respuesta" en cada uno de esos campos: el
   * valor entra en el borrador con `accept_default` y de ahí al envío por el
   * camino de siempre. Ni el cuerpo de la petición ni el tipo de `AnswerItem`
   * cambian; lo único que cambia es que la pulsación es una y no dieciocho.
   */
  function aplicarSugerencias(): void {
    const copia = { ...borradores.value };
    let cambio = false;

    for (const sugerencia of sugerenciasPendientes.value) {
      copia[sugerencia.field_code] = {
        valor: sugerencia.value as ValorCampo,
        interaccion: "accept_default",
      };
      sembrados.delete(sugerencia.field_code);
      tocados.value.add(sugerencia.field_code);
      cambio = true;
    }

    if (cambio) borradores.value = copia;
  }

  /**
   * Enseña las sugerencias que quedaron pendientes para que se puedan editar.
   *
   * No las aplica: el campo sigue como estaba y la sugerencia vuelve a ser lo
   * que era antes de esconderla, una ayuda con su botón. Lo que no se toque en
   * la revisión lo recoge `aplicarSugerencias` al guardar, así que revisar y no
   * cambiar nada acaba en el mismo envío que no revisar.
   */
  function revelarSugerencias(): void {
    const abiertos = new Set(revelados.value);
    for (const sugerencia of sugerenciasPendientes.value) abiertos.add(sugerencia.field_code);
    revelados.value = abiertos;
  }

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
    tocados.value.add(campo);
    borradores.value = { ...borradores.value, [campo]: { valor, interaccion } };
  }

  function borrar(campo: FieldCode): void {
    sembrados.delete(campo);
    tocados.value.delete(campo);
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
    aPreguntar,
    sugerencias,
    sugerenciasPendientes,
    contestadas,
    yaEnviado,
    cargarPlan,
    sugerenciaVisible,
    aplicarSugerencias,
    revelarSugerencias,
    responder,
    borrar,
    enviar,
  };
}
