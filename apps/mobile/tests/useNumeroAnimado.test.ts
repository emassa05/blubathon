import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope, ref } from "vue";

import { useNumeroAnimado } from "@/composables/useNumeroAnimado";

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

    reiniciar();

    // El cero es inmediato: es lo que hace que se vea la cuenta entera.
    expect(mostrado.value).toBe(0);

    vi.advanceTimersByTime(DURACION);
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
