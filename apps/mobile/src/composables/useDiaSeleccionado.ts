import { computed, ref } from "vue";

/** "martes 25" */
const FORMATO_DIA = new Intl.DateTimeFormat("es-ES", { weekday: "long", day: "numeric" });

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
 * fecha en minúscula, para incrustarla en un `aria-label`.
 */
export function useDiaSeleccionado(fechaInicial: string) {
  const dia = ref<Date>(desdeIso(fechaInicial));

  const etiqueta = computed(() => conMayuscula(FORMATO_DIA.format(dia.value)));
  const etiquetaAccesible = computed(() => FORMATO_DIA.format(dia.value));

  /** El mismo día en ISO local (`YYYY-MM-DD`): así lo nombra la API. */
  const fechaIso = computed(() => {
    const mes = String(dia.value.getMonth() + 1).padStart(2, "0");
    return `${dia.value.getFullYear()}-${mes}-${String(dia.value.getDate()).padStart(2, "0")}`;
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
