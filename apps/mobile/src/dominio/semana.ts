/**
 * La semana del calendario: de lunes a domingo, y cómo se mueve.
 *
 * Todas las fechas viajan como ISO local (`YYYY-MM-DD`), que es la forma en la
 * que la API habla de un día (`local_date`). Se construyen con la hora explícita
 * porque `new Date("2026-08-25")` se interpreta en UTC y el día mostrado bailaría
 * según la zona horaria del dispositivo.
 */

const DIAS_POR_SEMANA = 7;

const FORMATO_INICIAL = new Intl.DateTimeFormat("es-ES", { weekday: "narrow" });
const FORMATO_NOMBRE = new Intl.DateTimeFormat("es-ES", { weekday: "long" });
const FORMATO_DIA_MES = new Intl.DateTimeFormat("es-ES", { day: "numeric", month: "long" });
const FORMATO_DIA_MES_ANIO = new Intl.DateTimeFormat("es-ES", {
  day: "numeric",
  month: "long",
  year: "numeric",
});
const FORMATO_DIA = new Intl.DateTimeFormat("es-ES", { day: "numeric" });
const FORMATO_LARGO = new Intl.DateTimeFormat("es-ES", {
  weekday: "long",
  day: "numeric",
  month: "long",
});

export interface DiaCalendario {
  /** `YYYY-MM-DD`, el mismo `local_date` que usa la API. */
  readonly iso: string;
  readonly numero: number;
  /** Inicial del día para la cabecera del calendario: L, M, X, J, V, S, D. */
  readonly inicial: string;
  readonly nombre: string;
  readonly esHoy: boolean;
  /** Un día que todavía no ha pasado no puede tener cuestionario. */
  readonly esFuturo: boolean;
}

export interface Semana {
  /** ISO del lunes. Identifica la semana. */
  readonly inicio: string;
  /** ISO del domingo. */
  readonly fin: string;
  readonly dias: readonly DiaCalendario[];
  /** "25 – 31 de agosto" */
  readonly etiqueta: string;
  /** La misma semana, entera y sin abreviar, para el nombre accesible. */
  readonly etiquetaAccesible: string;
  readonly esSemanaActual: boolean;
}

export function desdeIso(iso: string): Date {
  return new Date(`${iso}T00:00:00`);
}

export function aIso(fecha: Date): string {
  const mes = String(fecha.getMonth() + 1).padStart(2, "0");
  const dia = String(fecha.getDate()).padStart(2, "0");
  return `${fecha.getFullYear()}-${mes}-${dia}`;
}

/** El día de hoy del dispositivo, en ISO local. */
export function hoyIso(): string {
  return aIso(new Date());
}

export function conMayuscula(texto: string): string {
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

/** El lunes de la semana a la que pertenece esa fecha. */
export function lunesDe(iso: string): string {
  const fecha = desdeIso(iso);
  // `getDay()` da 0 en domingo: el domingo pertenece a la semana que empezó seis días antes.
  const desplazamiento = (fecha.getDay() + 6) % DIAS_POR_SEMANA;
  fecha.setDate(fecha.getDate() - desplazamiento);
  return aIso(fecha);
}

/** La misma semana, `cantidad` semanas más adelante o más atrás. */
export function desplazarSemana(inicioIso: string, cantidad: number): string {
  const fecha = desdeIso(inicioIso);
  fecha.setDate(fecha.getDate() + cantidad * DIAS_POR_SEMANA);
  return aIso(fecha);
}

/** "Martes 25 de agosto", para titular un día. */
export function etiquetaDiaLargo(iso: string): string {
  return conMayuscula(FORMATO_LARGO.format(desdeIso(iso)));
}

/**
 * El rótulo de la semana, sin repetir lo que ya se sabe: el mes solo aparece
 * dos veces si la semana cambia de mes, y el año solo si cambia de año.
 */
function etiquetaDeRango(inicio: Date, fin: Date): string {
  if (inicio.getFullYear() !== fin.getFullYear()) {
    return `${FORMATO_DIA_MES_ANIO.format(inicio)} – ${FORMATO_DIA_MES_ANIO.format(fin)}`;
  }
  if (inicio.getMonth() !== fin.getMonth()) {
    return `${FORMATO_DIA_MES.format(inicio)} – ${FORMATO_DIA_MES.format(fin)}`;
  }
  return `${FORMATO_DIA.format(inicio)} – ${FORMATO_DIA_MES.format(fin)}`;
}

export function semanaDe(iso: string, hoy: string = hoyIso()): Semana {
  const inicioIso = lunesDe(iso);
  const inicio = desdeIso(inicioIso);
  const dias: DiaCalendario[] = [];

  for (let indice = 0; indice < DIAS_POR_SEMANA; indice += 1) {
    const fecha = desdeIso(inicioIso);
    fecha.setDate(fecha.getDate() + indice);
    const diaIso = aIso(fecha);
    dias.push({
      iso: diaIso,
      numero: fecha.getDate(),
      inicial: conMayuscula(FORMATO_INICIAL.format(fecha)),
      nombre: conMayuscula(FORMATO_NOMBRE.format(fecha)),
      esHoy: diaIso === hoy,
      esFuturo: diaIso > hoy,
    });
  }

  const finIso = dias[DIAS_POR_SEMANA - 1]?.iso ?? inicioIso;
  const fin = desdeIso(finIso);

  return {
    inicio: inicioIso,
    fin: finIso,
    dias,
    etiqueta: etiquetaDeRango(inicio, fin),
    etiquetaAccesible: `Semana del ${FORMATO_DIA_MES_ANIO.format(inicio)} al ${FORMATO_DIA_MES_ANIO.format(fin)}`,
    esSemanaActual: inicioIso === lunesDe(hoy),
  };
}

const FORMATO_CORTO = new Intl.DateTimeFormat("es-ES", { weekday: "long", day: "numeric" });

/** "Lunes 24", el mismo rótulo que usa la lista de últimos formularios. */
export function etiquetaDiaCorto(iso: string): string {
  return conMayuscula(FORMATO_CORTO.format(desdeIso(iso)));
}
