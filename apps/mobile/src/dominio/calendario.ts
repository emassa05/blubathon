/**
 * El mes del calendario: sus días, cómo se agrupan en semanas y cómo se mueve.
 *
 * Todas las fechas viajan como ISO local (`YYYY-MM-DD`), que es la forma en la
 * que la API habla de un día (`local_date`). Se construyen con la hora explícita
 * porque `new Date("2026-08-25")` se interpreta en UTC y el día mostrado bailaría
 * según la zona horaria del dispositivo.
 */

const DIAS_POR_SEMANA = 7;

const FORMATO_INICIAL = new Intl.DateTimeFormat("es-ES", { weekday: "narrow" });
const FORMATO_NOMBRE = new Intl.DateTimeFormat("es-ES", { weekday: "long" });
const FORMATO_MES_ANIO = new Intl.DateTimeFormat("es-ES", { month: "long", year: "numeric" });
const FORMATO_LARGO = new Intl.DateTimeFormat("es-ES", {
  weekday: "long",
  day: "numeric",
  month: "long",
});

export interface DiaCalendario {
  /** `YYYY-MM-DD`, el mismo `local_date` que usa la API. */
  readonly iso: string;
  readonly numero: number;
  /** Inicial del día: L, M, X, J, V, S, D. */
  readonly inicial: string;
  readonly nombre: string;
  readonly esHoy: boolean;
  /** Un día que todavía no ha pasado no puede tener cuestionario. */
  readonly esFuturo: boolean;
}

export interface Mes {
  /** ISO del día 1. Identifica el mes. */
  readonly inicio: string;
  /** ISO del último día del mes. */
  readonly fin: string;
  readonly dias: readonly DiaCalendario[];
  /**
   * Columnas vacías antes del día 1, de 0 a 6.
   *
   * La rejilla empieza en lunes, así que un mes que abre en jueves deja tres
   * huecos: sin ellos, el día 1 caería bajo la columna equivocada y todo el mes
   * quedaría corrido respecto a su día de la semana.
   */
  readonly huecoInicial: number;
  /** "Agosto de 2026" */
  readonly etiqueta: string;
  /** Lo mismo, para el nombre accesible; aquí no hay nada que abreviar. */
  readonly etiquetaAccesible: string;
  readonly esMesActual: boolean;
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

/**
 * Las iniciales de la cabecera, de lunes a domingo.
 *
 * En la rejilla mensual la inicial deja de vivir en cada celda y pasa a la
 * cabecera: repetirla treinta y una veces es ruido, y la columna ya la dice.
 * Se derivan del propio formato de `es-ES` y no de una lista escrita a mano.
 */
export const INICIALES_SEMANA: readonly string[] = Array.from(
  { length: DIAS_POR_SEMANA },
  // 2024-01-01 fue lunes: sirve de semana de referencia y no se muestra nunca.
  (_, indice) => conMayuscula(FORMATO_INICIAL.format(new Date(2024, 0, 1 + indice))),
);

/** El día 1 del mes al que pertenece esa fecha. */
export function primeroDe(iso: string): string {
  const fecha = desdeIso(iso);
  fecha.setDate(1);
  return aIso(fecha);
}

/**
 * El mismo mes, `cantidad` meses más adelante o más atrás.
 *
 * Se opera siempre sobre el día 1, así que no hay desbordes: `setMonth` sobre un
 * 31 de enero daría 2 o 3 de marzo, sobre un 1 nunca.
 */
export function desplazarMes(inicioIso: string, cantidad: number): string {
  const fecha = desdeIso(primeroDe(inicioIso));
  fecha.setMonth(fecha.getMonth() + cantidad);
  return aIso(fecha);
}

/** "Martes 25 de agosto", para titular un día. */
export function etiquetaDiaLargo(iso: string): string {
  return conMayuscula(FORMATO_LARGO.format(desdeIso(iso)));
}

export function mesDe(iso: string, hoy: string = hoyIso()): Mes {
  const inicioIso = primeroDe(iso);
  const inicio = desdeIso(inicioIso);
  // El día 0 del mes siguiente es el último de este: evita la tabla de 28/30/31
  // y los años bisiestos.
  const cuantosDias = new Date(inicio.getFullYear(), inicio.getMonth() + 1, 0).getDate();

  const dias: DiaCalendario[] = [];
  for (let indice = 0; indice < cuantosDias; indice += 1) {
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

  const etiqueta = conMayuscula(FORMATO_MES_ANIO.format(inicio));

  return {
    inicio: inicioIso,
    fin: dias[cuantosDias - 1]?.iso ?? inicioIso,
    dias,
    // `getDay()` da 0 en domingo, que en una semana que abre en lunes es la
    // séptima columna, no la primera.
    huecoInicial: (inicio.getDay() + 6) % DIAS_POR_SEMANA,
    etiqueta,
    etiquetaAccesible: etiqueta,
    esMesActual: inicioIso === primeroDe(hoy),
  };
}
