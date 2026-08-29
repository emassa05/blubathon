import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope, ref } from "vue";

import {
  MS_CUENTA,
  MS_CUENTA_DESDE_CERO,
  useNumeroAnimado,
} from "@/composables/useNumeroAnimado";

/**
 * La animación va con `requestAnimationFrame` y mide con `performance.now`, así
 * que se falsean los dos: sin `performance` el reloj no avanzaría y el primer
 * fotograma se quedaría siempre en el 0% del recorrido.
 */
beforeEach(() => {
  vi.useFakeTimers({
    toFake: ["requestAnimationFrame", "cancelAnimationFrame", "performance"],
  });
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

const DURACION = 100;

/** Monta el composable en su propio ámbito, que es lo que pide `onScopeDispose`. */
function montar(inicial: number | null) {
  const destino = ref<number | null>(inicial);
  const ambito = effectScope();
  const animado = ambito.run(() => useNumeroAnimado(destino, DURACION))!;
  return { destino, ...animado, parar: () => ambito.stop() };
}

describe("useNumeroAnimado", () => {
  it("nace con el valor puesto, sin animar nada", () => {
    const { mostrado, parar } = montar(18);

    expect(mostrado.value).toBe(18);
    parar();
  });

  it("recorre del valor anterior al nuevo cuando el destino cambia", async () => {
    const { destino, mostrado, parar } = montar(18);

    destino.value = 22;
    await Promise.resolve();

    // A media animación va por el camino, no en ninguno de los dos extremos.
    vi.advanceTimersByTime(DURACION / 2);
    expect(mostrado.value).toBeGreaterThan(18);
    expect(mostrado.value).toBeLessThan(22);

    vi.advanceTimersByTime(DURACION);
    expect(mostrado.value).toBe(22);
    parar();
  });

  it("reiniciar cae a cero y vuelve a subir hasta el mismo valor", () => {
    const { mostrado, reiniciar, parar } = montar(18);

    reiniciar(DURACION);

    // El cero es inmediato: es lo que hace que se vea la cuenta entera.
    expect(mostrado.value).toBe(0);

    vi.advanceTimersByTime(DURACION);
    expect(mostrado.value).toBe(18);
    parar();
  });

  it("la cuenta desde cero sale despacio en vez de aparecer casi puesta", () => {
    const { mostrado, reiniciar, parar } = montar(100);

    reiniciar(DURACION);

    // Al 10% del tiempo va por el 0.4% del recorrido, no por el 27% que daría
    // la curva de la corrección: es lo que hace que se lea que empieza en cero.
    vi.advanceTimersByTime(DURACION / 10);
    expect(mostrado.value).toBeLessThan(5);

    // Y a la mitad va por la mitad, así que no se queda atascada abajo.
    vi.advanceTimersByTime(DURACION * 0.4);
    expect(mostrado.value).toBeGreaterThan(40);
    expect(mostrado.value).toBeLessThan(60);

    vi.advanceTimersByTime(DURACION);
    expect(mostrado.value).toBe(100);
    parar();
  });

  it("la cuenta desde cero dura más que la corrección", () => {
    const { mostrado, reiniciar, parar } = montar(50);

    // Sin duración explícita usa la suya, que es la larga.
    reiniciar();

    vi.advanceTimersByTime(MS_CUENTA);
    expect(mostrado.value).toBeLessThan(50);

    vi.advanceTimersByTime(MS_CUENTA_DESDE_CERO);
    expect(mostrado.value).toBe(50);
    parar();
  });

  it("armada, el valor nuevo no asoma: la cifra se queda en cero", async () => {
    const { destino, mostrado, reiniciar, prepararCuenta, parar } = montar(18);

    // Se arma al enviar, con el diálogo aún tapando la pantalla.
    prepararCuenta();
    expect(mostrado.value).toBe(0);

    // El resumen se recarga y llega la cifra nueva. Antes se animaba aquí, y
    // como el diálogo tarda en irse, se leía el resultado durante la salida y
    // volvía a caer a cero al arrancar la cuenta.
    destino.value = 42;
    await Promise.resolve();
    vi.advanceTimersByTime(MS_CUENTA * 2);
    expect(mostrado.value).toBe(0);

    // Y al cerrar, la cuenta entera y una sola vez.
    reiniciar(DURACION);
    expect(mostrado.value).toBe(0);
    vi.advanceTimersByTime(DURACION);
    expect(mostrado.value).toBe(42);
    parar();
  });

  it("armada sin animación, la cifra se recoge en vez de quedarse en cero", () => {
    vi.stubGlobal(
      "matchMedia",
      vi.fn(() => ({ matches: true })),
    );

    const { mostrado, reiniciar, prepararCuenta, parar } = montar(18);

    // Con menos movimiento no se arma nada, así que no hay cero que recoger.
    prepararCuenta();
    expect(mostrado.value).toBe(18);

    reiniciar();
    expect(mostrado.value).toBe(18);
    parar();
  });

  it("reiniciar no hace nada sin cifra: no hay recorrido que enseñar", () => {
    const { mostrado, reiniciar, parar } = montar(null);

    reiniciar();

    expect(mostrado.value).toBeNull();
    parar();
  });

  it("con menos movimiento la cifra se queda puesta en vez de parpadear", () => {
    vi.stubGlobal(
      "matchMedia",
      vi.fn(() => ({ matches: true })),
    );

    const { mostrado, reiniciar, parar } = montar(18);

    reiniciar();

    // Ni un fotograma en cero: poner el cero para borrarlo acto seguido es
    // exactamente el movimiento que se pidió no hacer.
    expect(mostrado.value).toBe(18);
    parar();
  });
});
