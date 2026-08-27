/**
 * El catálogo de campos diarios, en la forma que necesita la interfaz.
 *
 * Todo sale de `@contrato`: los campos, sus tipos, sus rangos, sus valores
 * permitidos, sus etiquetas y sus anclas. Aquí no se declara ni un campo, ni un
 * rango, ni un texto visible: solo se normaliza la forma del catálogo generado
 * —donde cada entrada trae unas claves u otras según su tipo— a una estructura
 * uniforme que un componente puede recorrer sin preguntar por el tipo.
 */

import { BLUBATHON_FIELD_CATALOG, BLUBATHON_TEXTS_ES, type FieldCode, type ValorCampo } from "@/api/contrato";

export type TipoCampo =
  "continuous" | "count" | "ordinal" | "nominal" | "boolean" | "tag_set" | "text";

export interface EspecificacionCampo {
  readonly codigo: FieldCode;
  readonly tipo: TipoCampo;
  readonly origenes: readonly string[];
  /** Solo en `continuous`, `count` y `ordinal`. */
  readonly minimo?: number;
  readonly maximo?: number;
  /** Solo en `nominal`. */
  readonly valores?: readonly string[];
  /** Solo en `text`. */
  readonly largoMaximo?: number;
}

function normalizar(entrada: (typeof BLUBATHON_FIELD_CATALOG.fields)[number]): EspecificacionCampo {
  return {
    codigo: entrada.code,
    tipo: entrada.kind,
    origenes: entrada.allowedSources,
    ...("minimum" in entrada ? { minimo: entrada.minimum } : {}),
    ...("maximum" in entrada ? { maximo: entrada.maximum } : {}),
    ...("allowedValues" in entrada ? { valores: entrada.allowedValues } : {}),
    ...("maxLength" in entrada ? { largoMaximo: entrada.maxLength } : {}),
  };
}

const ESPECIFICACIONES = new Map<FieldCode, EspecificacionCampo>(
  BLUBATHON_FIELD_CATALOG.fields.map((entrada) => [entrada.code, normalizar(entrada)]),
);

export function especificacionCampo(codigo: FieldCode): EspecificacionCampo | undefined {
  return ESPECIFICACIONES.get(codigo);
}

/**
 * El origen del cuestionario del cuidador.
 *
 * El contrato lo llama `caregiver_daily` y el servidor lo guarda como `home`
 * (`apps/api/services/submissions.py: _stored_source`); la matriz de fuentes del
 * catálogo está escrita con el segundo nombre.
 */
export const ORIGEN_CASA = "home";

/** Los campos que el cuestionario de casa puede preguntar, en orden canónico. */
export const CAMPOS_DE_CASA: readonly FieldCode[] = BLUBATHON_FIELD_CATALOG.canonicalOrder.filter(
  (codigo) => especificacionCampo(codigo)?.origenes.includes(ORIGEN_CASA) ?? false,
);

/** Posición de un campo en el orden canónico. Ordena listas sin inventar criterio. */
export function ordenCanonico(codigo: FieldCode): number {
  const posicion = BLUBATHON_FIELD_CATALOG.canonicalOrder.indexOf(codigo);
  return posicion === -1 ? BLUBATHON_FIELD_CATALOG.canonicalOrder.length : posicion;
}

export function etiquetaCampo(codigo: FieldCode): string {
  return BLUBATHON_TEXTS_ES.fieldLabelsEs[codigo] ?? codigo;
}

export function preguntaCampo(codigo: FieldCode): string {
  return BLUBATHON_TEXTS_ES.fieldPromptsEs[codigo] ?? etiquetaCampo(codigo);
}

/** Las etiquetas de los valores de cada campo nominal, tal y como las publica el contrato. */
const ETIQUETAS_POR_CAMPO: Partial<Record<FieldCode, Readonly<Record<string, string>>>> = {
  sleep_quality: BLUBATHON_TEXTS_ES.sleepQualityLabelsEs,
  wake_state: BLUBATHON_TEXTS_ES.wakeStateLabelsEs,
  gi_status: BLUBATHON_TEXTS_ES.giStatusLabelsEs,
  medication_adherence: BLUBATHON_TEXTS_ES.medicationAdherenceLabelsEs,
  alertness: BLUBATHON_TEXTS_ES.alertnessLabelsEs,
  daily_regulation_state: BLUBATHON_TEXTS_ES.dailyRegulationLabelsEs,
  attendance_status: BLUBATHON_TEXTS_ES.attendanceLabelsEs,
};

export function etiquetaOpcion(codigo: FieldCode, valor: string): string {
  return ETIQUETAS_POR_CAMPO[codigo]?.[valor] ?? valor;
}

const ANCLAS = BLUBATHON_TEXTS_ES.ordinalAnchorsEs as Readonly<Record<string, readonly string[]>>;

/** El ancla de un punto de la escala: "3 - Apoyo moderado". Nunca se inventa. */
export function anclaOrdinal(codigo: FieldCode, valor: number): string {
  const anclas = ANCLAS[codigo];
  const ancla = anclas?.[valor - 1];
  if (ancla === undefined) return String(valor);
  // El ancla ya trae el número delante: "3 - Apoyo moderado".
  const separador = ancla.indexOf(" - ");
  return separador === -1 ? ancla : ancla.slice(separador + 3);
}

/** Los puntos de una escala ordinal, sacados de su propio rango del catálogo. */
export function escalaOrdinal(especificacion: EspecificacionCampo): readonly number[] {
  const minimo = especificacion.minimo ?? 1;
  const maximo = especificacion.maximo ?? minimo;
  return Array.from({ length: maximo - minimo + 1 }, (_, indice) => minimo + indice);
}

/**
 * Los campos que el cuestionario pinta como cifra con dos pasos, y no como
 * pastillas ni como escala: las horas de sueño, los despertares, los episodios.
 * Un ordinal también es un número, pero se contesta pulsando uno de sus cinco
 * puntos, así que no tiene campo que rellenar.
 */
export function esNumerico(especificacion: EspecificacionCampo): boolean {
  return especificacion.tipo === "continuous" || especificacion.tipo === "count";
}

/**
 * El valor con el que nace un campo numérico.
 *
 * Es 1 y no el mínimo del rango, que en los tres campos de casa es 0. Un 0 de
 * salida se lee como una respuesta —"no durmió", "ningún despertar"— y un campo
 * vacío obliga a escribir antes de poder usar los pasos. El 1 no dice nada
 * plausible por sí solo y deja los dos pasos operativos desde el principio.
 *
 * Se acota contra el rango del catálogo por si un campo futuro empezara más
 * arriba: el valor inicial nunca puede caer fuera de lo que el contrato admite.
 */
export const VALOR_NUMERICO_INICIAL = 1;

export function valorInicialNumerico(especificacion: EspecificacionCampo): number {
  const minimo = especificacion.minimo ?? VALOR_NUMERICO_INICIAL;
  const maximo = especificacion.maximo ?? VALOR_NUMERICO_INICIAL;
  return Math.min(maximo, Math.max(minimo, VALOR_NUMERICO_INICIAL));
}

/** Unidad visible de los campos que la tienen. El resto no lleva ninguna. */
const UNIDADES: Partial<Record<FieldCode, string>> = {
  sleep_hours: "h",
};

/** Un valor guardado, escrito para que se lea: "6.2 h", "Interrumpido", "Sí". */
export function formatearValor(codigo: FieldCode, valor: ValorCampo): string {
  const especificacion = especificacionCampo(codigo);
  if (typeof valor === "boolean") return valor ? "Sí" : "No";
  // Lo único de tipo objeto que admite el contrato es la lista de etiquetas.
  if (typeof valor === "object") return valor.length === 0 ? "—" : valor.join(", ");
  if (typeof valor === "string") return etiquetaOpcion(codigo, valor);
  if (especificacion?.tipo === "ordinal") {
    return `${valor}/${especificacion.maximo ?? 5} · ${anclaOrdinal(codigo, valor)}`;
  }
  const unidad = UNIDADES[codigo];
  return unidad === undefined ? String(valor) : `${valor} ${unidad}`;
}

/** Una respuesta guardada de un día: campo → valor. */
export type RespuestasDelDia = Readonly<Partial<Record<FieldCode, ValorCampo>>>;
