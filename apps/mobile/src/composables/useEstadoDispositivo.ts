import { onBeforeUnmount, onMounted, ref } from "vue";

import { ESTADO_DISPOSITIVO_MOCK } from "@/data/saludMock";
import { INTERVALO_RELOJ_MS } from "@/theme/tokens";

/** Lo poco que usamos de la Battery Status API, que no está en lib.dom. */
interface GestorBateria {
  readonly level: number;
  addEventListener(tipo: "levelchange", escucha: () => void): void;
  removeEventListener(tipo: "levelchange", escucha: () => void): void;
}

type NavegadorConBateria = Navigator & {
  getBattery?: () => Promise<GestorBateria>;
};

const FORMATO_HORA = new Intl.DateTimeFormat("es-ES", {
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

/**
 * Único punto de entrada de la barra de estado: hora del sistema y batería.
 *
 * La batería sale de `navigator.getBattery()` cuando el navegador la expone; si
 * no existe o falla, se queda el valor del mock sin ruido ni aviso.
 */
export function useEstadoDispositivo() {
  const hora = ref<string>(ESTADO_DISPOSITIVO_MOCK.hora);
  const bateria = ref<number>(ESTADO_DISPOSITIVO_MOCK.bateria);

  let temporizador: ReturnType<typeof setInterval> | undefined;
  let gestor: GestorBateria | undefined;
  let alCambiarNivel: (() => void) | undefined;

  function refrescarHora(): void {
    hora.value = FORMATO_HORA.format(new Date());
  }

  onMounted(async () => {
    refrescarHora();
    temporizador = setInterval(refrescarHora, INTERVALO_RELOJ_MS);

    // `as` acotado: sondear una API opcional del navegador es justo el caso en
    // el que lib.dom se queda corta.
    const navegador = navigator as NavegadorConBateria;
    if (typeof navegador.getBattery !== "function") return;

    try {
      const encontrado = await navegador.getBattery();
      gestor = encontrado;
      alCambiarNivel = () => {
        bateria.value = Math.round(encontrado.level * 100);
      };
      alCambiarNivel();
      encontrado.addEventListener("levelchange", alCambiarNivel);
    } catch {
      // Degradación silenciosa: se mantiene el valor del mock.
    }
  });

  onBeforeUnmount(() => {
    if (temporizador !== undefined) clearInterval(temporizador);
    if (gestor !== undefined && alCambiarNivel !== undefined) {
      gestor.removeEventListener("levelchange", alCambiarNivel);
    }
  });

  return { hora, bateria };
}
