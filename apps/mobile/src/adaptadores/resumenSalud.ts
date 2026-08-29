/**
 * De las respuestas del backend al contrato de la pantalla.
 *
 * Es el único sitio donde conviven los dos vocabularios. La API habla de
 * episodios, tracks, abstenciones y `field_code`; la pantalla habla de riesgo,
 * confianza, factores y formularios. Traducir aquí y en un solo sentido deja a
 * los componentes sin nada que saber de HTTP, y a la API sin nada que saber del
 * diseño.
 *
 * Cuando el backend no tiene un dato, aquí **no se inventa**. La abstención del
 * modelo viaja como `riesgo: null` hasta la cabecera, que la dibuja como lo que
 * es: una estimación que no existe.
 */

import type {
  ChildHistoryDay,
  FieldCode,
  FormPlanResponse,
  FormQuestion,
  RecommendationInstanceView,
  TodayRecommendationResponse,
} from "@blubathon/contract/contract";
import { BLUBATHON_CONSTANTS } from "@blubathon/contract/constants";
import { BLUBATHON_TEXTS_ES } from "@blubathon/contract/texts";

import { DIAS_HISTORIAL } from "@/api/config";
import { ErrorBlubathon } from "@/api/errores";
import {
  historialNino,
  planFormulario,
  recomendacionDeEpisodio,
  recomendacionDeHoy,
} from "@/api/blubathon";
import { fechaDeHoy } from "@/composables/useDiaSeleccionado";
import { confianzaDelIntervalo } from "@/dominio/incertidumbre";
import { unificarPorDia } from "@/dominio/historial";
import { rachaSinDesregulacion } from "@/dominio/rachas";
import { reconciliar, respuestasDe } from "@/estado/respuestas";
import type {
  EstadoRedaccion,
  FactorRiesgo,
  IconoFactor,
  RegistroFormulario,
  ResumenSalud,
} from "@/types/salud";

/** Días que lista "Últimos formularios", empezando por el visible. */
const DIAS_EN_LISTA = 4;

/** "lunes 24" → la fila del listado. */
const FORMATO_FILA = new Intl.DateTimeFormat("es-ES", { weekday: "long", day: "numeric" });

const CAMPOS_DE_SUENO: ReadonlySet<FieldCode> = new Set<FieldCode>([
  "sleep_hours",
  "sleep_quality",
  "night_awakenings",
  "wake_state",
]);

/** C14: un campo se considera vencido a los 7 días. */
const DIAS_VENCIMIENTO = BLUBATHON_CONSTANTS.C14.value;

/**
 * `days_since_presented` no viaja en `FormQuestion`, así que el texto no puede
 * dar el número exacto. Dice el umbral, que es lo que el motivo significa: el
 * backend marca `staleness` cuando pasaron `C14` días o cuando el campo no se
 * ha registrado nunca.
 */
const DETALLE_POR_MOTIVO: Record<FormQuestion["reason"], string> = {
  staleness: `Sin registrar en los últimos ${DIAS_VENCIMIENTO} días`,
  exploration: "Turno de exploración de esta semana",
  canonical_order: "Por orden del formulario",
};

/**
 * El contrato marca opcional casi todo lo que puede faltar, así que ausente
 * llega unas veces como `null` y otras como `undefined`. Esto los junta en uno.
 */
function presente<T>(valor: T | null | undefined): valor is T {
  return valor !== null && valor !== undefined;
}

/* Riesgo ------------------------------------------------------------------ */

function porcentaje(probabilidad: number): number {
  return Math.round(probabilidad * 100);
}

/* Recomendación ----------------------------------------------------------- */

const SIN_FORMULARIO =
  "Todavía no hay formulario de este día. Al enviarlo aparece la recomendación.";
const EN_CURSO = "Estamos preparando la recomendación de este día.";
const SIN_RECOMENDACION = "Este día no tiene recomendación.";

/**
 * Los tres motivos por los que el sistema decide **no** recomendar.
 *
 * Abstenerse no es un fallo, y el backend lo devuelve como 200 con motivo
 * explícito: la pantalla tiene que decir por qué no hay consejo, no
 * dejar la tarjeta en blanco ni rellenarla con un consejo genérico.
 */
const TEXTO_ABSTENCION: Record<string, string> = {
  no_indexed_match: "No hay material indexado que respalde una recomendación para este día.",
  draft_unavailable: "La redacción no está disponible en este momento.",
  draft_not_grounded: "La redacción no quedó respaldada por sus fuentes, así que no se muestra.",
};

type EstadoRecomendacion = Pick<
  TodayRecommendationResponse,
  "status" | "action_text_es" | "abstention_reason"
>;

/**
 * El texto del día y en qué punto está su redacción.
 *
 * El estado no es decoración: `pendiente` significa que el RAG sigue redactando
 * y que la respuesta va a cambiar sola, y es lo único que la tarjeta anima. Sin
 * este dato la pantalla no puede distinguir "todavía no hay consejo" de "no va a
 * haberlo", que para quien mira son cosas muy distintas.
 */
function leerRecomendacion(estado: EstadoRecomendacion | null): {
  texto: string;
  estado: EstadoRedaccion;
} {
  if (estado === null) return { texto: SIN_RECOMENDACION, estado: "abstenida" };
  switch (estado.status) {
    case "matched":
      return { texto: estado.action_text_es ?? SIN_RECOMENDACION, estado: "lista" };
    case "pending":
      return { texto: EN_CURSO, estado: "pendiente" };
    case "abstained":
      return {
        texto: TEXTO_ABSTENCION[estado.abstention_reason ?? ""] ?? SIN_RECOMENDACION,
        estado: "abstenida",
      };
    case "no_submission_today":
      return { texto: SIN_FORMULARIO, estado: "sin-formulario" };
  }
}

function desdeVistaDeEpisodio(vista: RecommendationInstanceView): EstadoRecomendacion {
  return {
    status: vista.status,
    action_text_es: vista.action_text_es,
    abstention_reason: vista.abstention_reason,
  };
}

/* Factores ---------------------------------------------------------------- */

/**
 * "Lo más importante hoy" son las preguntas que el formulario destaca.
 *
 * El backend no publica importancias del modelo —el track visible es una tasa
 * observada, sin predictores que ponderar—, así que la señal más cercana y
 * honesta es la política del formulario: los campos que hoy pide
 * primero, por antigüedad, exploración o valor de información. Por eso la
 * tarjeta habla de lo que el formulario prioriza y no de causas del riesgo.
 */
function factores(plan: FormPlanResponse | null): readonly FactorRiesgo[] {
  if (plan === null) return [];
  return (plan.questions ?? [])
    .filter((pregunta) => pregunta.highlighted)
    .map((pregunta) => ({
      id: pregunta.field_code,
      icono: (CAMPOS_DE_SUENO.has(pregunta.field_code) ? "luna" : "rombo") satisfies IconoFactor,
      titulo: BLUBATHON_TEXTS_ES.fieldLabelsEs[pregunta.field_code],
      detalle: DETALLE_POR_MOTIVO[pregunta.reason],
      prioridad: "alta" as const,
    }));
}

/* Formularios ------------------------------------------------------------- */

function diaAnteriorA(fechaIso: string, dias: number): string {
  const fecha = new Date(`${fechaIso}T00:00:00`);
  fecha.setDate(fecha.getDate() - dias);
  const mes = String(fecha.getMonth() + 1).padStart(2, "0");
  const numero = String(fecha.getDate()).padStart(2, "0");
  return `${fecha.getFullYear()}-${mes}-${numero}`;
}

/**
 * El listado va por calendario, no por lo que trae el historial.
 *
 * `GET /history` solo devuelve días **con** envío, así que recorrerlo dejaría
 * todas las filas en "Respondido" y el hueco —que es justo lo que hay que
 * ver— desaparecería.
 *
 * Empieza en el día visible y no en el anterior. Antes lo saltaba porque hoy
 * tenía su propio aviso, pero ese aviso solo se dibuja mientras el formulario
 * está pendiente: al enviarlo desaparecía, y el día se quedaba sin estar en
 * ningún sitio de la pantalla.
 */
function formularios(
  fechaIso: string,
  conEnvio: ReadonlySet<string>,
): readonly RegistroFormulario[] {
  const hoy = fechaDeHoy();
  return Array.from({ length: DIAS_EN_LISTA }, (_, indice) => {
    const fecha = diaAnteriorA(fechaIso, indice);
    const etiqueta = FORMATO_FILA.format(new Date(`${fecha}T00:00:00`));
    return {
      id: fecha,
      // "Hoy" se lee antes que "miércoles 26", y es la fila que más se pulsa.
      dia: fecha === hoy ? "Hoy" : etiqueta.charAt(0).toUpperCase() + etiqueta.slice(1),
      estado: conEnvio.has(fecha) ? ("respondido" as const) : ("sin-responder" as const),
    };
  });
}

/* Carga ------------------------------------------------------------------- */

async function recomendacionDelDia(
  dia: ChildHistoryDay | null,
  signal?: AbortSignal,
): Promise<EstadoRecomendacion | null> {
  const idEpisodio = dia?.prediction_episode_id;
  if (!presente(idEpisodio) || !presente(dia?.recommendation)) return null;
  try {
    return desdeVistaDeEpisodio(await recomendacionDeEpisodio(idEpisodio, signal));
  } catch (error) {
    // El episodio puede existir sin recomendación asociada: es un día vacío,
    // no un fallo que la pantalla deba mostrar.
    if (error instanceof ErrorBlubathon && error.esNoEncontrado) return null;
    throw error;
  }
}

export async function cargarResumenSalud(opciones: {
  idNino: string;
  fechaIso: string;
  signal?: AbortSignal;
}): Promise<ResumenSalud> {
  const { idNino, fechaIso, signal } = opciones;
  const esHoy = fechaIso === fechaDeHoy();

  // El historial va primero y solo: es la autoridad sobre qué días existen, y
  // hasta tenerlo la copia local puede estar mintiendo. Cuesta un viaje de más
  // en esta pantalla, y es el precio de no mandar respuestas fantasma al plan.
  const historial = await historialNino(idNino, { signal });
  /*
   * Un día por fecha, no uno por envío. Reenviar el cuestionario de un día
   * añade una fila de ese mismo día sin estimación ni resultado, y como el
   * endpoint la devuelve la primera, `find` se quedaba con ella: el riesgo
   * pasaba a `—` y la racha dejaba de ver el día. Ver `unificarPorDia`.
   */
  const dias = unificarPorDia(historial.days ?? []);
  const conEnvio = new Set(
    dias.filter((candidato) => presente(candidato.submission_id)).map((c) => c.local_date),
  );
  reconciliar(idNino, { conEnvio, completo: dias.length < DIAS_HISTORIAL });

  // `POST /form-plan` no lee la base: deriva los campos ya contestados **solo**
  // del cuerpo de la petición. Mandarlo vacío significaba "no hay nada
  // respondido", y por eso destacaba siempre los mismos dos campos aunque
  // acabaras de contestarlos. La copia local es lo único que sabe qué se envió.
  const yaRespondido = respuestasDe(idNino, fechaIso) ?? {};

  const [plan, deHoy] = await Promise.all([
    esHoy
      ? planFormulario(idNino, { source: "caregiver_daily", answers: yaRespondido }, signal)
      : Promise.resolve(null),
    esHoy ? recomendacionDeHoy(idNino, signal) : Promise.resolve(null),
  ]);

  const dia = dias.find((candidato) => candidato.local_date === fechaIso) ?? null;
  const estadoRecomendacion = deHoy ?? (await recomendacionDelDia(dia, signal));

  const prediccion = dia?.prediction ?? null;
  const probabilidad = prediccion?.status === "ok" ? prediccion.probability : null;
  const riesgo = presente(probabilidad) ? porcentaje(probabilidad) : null;

  return {
    fecha: fechaIso,
    riesgo,
    // Sin cifra no hay confianza que dar. Y con cifra puede seguir sin haberla:
    // el challenger logístico publica probabilidad y ningún intervalo, y es el
    // track preferido cuando estima. `null` en los dos casos.
    confianza: riesgo === null ? null : confianzaDelIntervalo(prediccion?.interval),
    recomendacion: leerRecomendacion(estadoRecomendacion),
    factores: factores(plan),
    formularios: formularios(fechaIso, conEnvio),
    formularioPendiente: !presente(dia?.submission_id),
    // De todo el historial y no solo del día visible: la racha es de la persona,
    // no de la fecha que se esté mirando.
    rachaSinDesregulacion: rachaSinDesregulacion(dias),
  };
}
