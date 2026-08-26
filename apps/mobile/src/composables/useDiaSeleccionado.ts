import { FARO_CONSTANTS } from "@faro/contract/constants";
import { computed, ref } from "vue";

/** "martes 25" */
const FORMATO_DIA = new Intl.DateTimeFormat("es-ES", { weekday: "long", day: "numeric" });

/**
 * El día no lo decide el reloj del dispositivo sino la zona de referencia del
 * sistema (SPEC 5.1 / C03). El backend agrupa los registros por esa fecha
 * local; si el móvil está en otro huso, la pantalla pediría el día equivocado.
 */
const ZONA_REFERENCIA = FARO_CONSTANTS.C03.value;

/** "en-CA" da exactamente YYYY-MM-DD, que es el formato que pide la API. */
const FORMATO_ISO = new Intl.DateTimeFormat("en-CA", {
  timeZone: ZONA_REFERENCIA,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

export function fechaDeHoy(): string {
  return FORMATO_ISO.format(new Date());
}

function conMayuscula(texto: string): string {
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

function desdeIso(fechaIso: string): Date {
  // Con la hora explícita el parseo es local; sin ella sería UTC y el día
  // mostrado podría bailar según la zona horaria.
  return new Date(`${fechaIso}T00:00:00`);
}

/**
 * Día que muestra la pantalla y las dos acciones del navegador de fecha.
 *
 * `etiqueta` es lo que se ve ("Martes 25"); `etiquetaAccesible` es la misma
 * fecha en minúscula, para incrustarla en un `aria-label`; `fechaIso` es la
 * clave con la que se le piden los datos a la API.
 */
export function useDiaSeleccionado(fechaInicial: string = fechaDeHoy()) {
  const dia = ref<Date>(desdeIso(fechaInicial));

  const etiqueta = computed(() => conMayuscula(FORMATO_DIA.format(dia.value)));
  const etiquetaAccesible = computed(() => FORMATO_DIA.format(dia.value));
  /** El mismo día en ISO local (`YYYY-MM-DD`): así lo nombra la API. */
  const fechaIso = computed(() => {
    const fecha = dia.value;
    const mes = String(fecha.getMonth() + 1).padStart(2, "0");
    const numero = String(fecha.getDate()).padStart(2, "0");
    return `${fecha.getFullYear()}-${mes}-${numero}`;
  });

  function desplazar(dias: number): void {
    const siguiente = new Date(dia.value);
    siguiente.setDate(siguiente.getDate() + dias);
    dia.value = siguiente;
  }

  return {
    dia,
    fechaIso,
    etiqueta,
    etiquetaAccesible,
    diaAnterior: () => desplazar(-1),
    diaSiguiente: () => desplazar(1),
  };
}
