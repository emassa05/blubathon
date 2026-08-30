import { describe, expect, it } from "vitest";

import { resumirConjunto } from "@/dominio/conjunto";
import type { FichaNino } from "@/types/terapeuta";

function ficha(parcial: Partial<FichaNino>): FichaNino {
  return {
    id: "id",
    etiqueta: "Niño",
    riesgo: null,
    serie: [],
    tasa: null,
    adherencia: 0,
    pendientes: 0,
    perfilSensorial: [],
    apoyosComunicacion: [],
    contraindicaciones: [],
    ...parcial,
  };
}

describe("resumirConjunto", () => {
  it("cuenta niños por banda en vez de promediar sus riesgos", () => {
    // Promediar líneas base personales es exactamente lo que el producto se
    // niega a hacer: cada niño se compara consigo mismo, así que la única
    // agregación honesta es contar cuántos hay en cada banda.
    const resumen = resumirConjunto([
      ficha({ riesgo: 80 }),
      ficha({ riesgo: 60 }),
      ficha({ riesgo: 30 }),
      ficha({ riesgo: 5 }),
      ficha({ riesgo: null }),
    ]);

    expect(resumen.porBanda).toEqual({ alto: 2, medio: 1, bajo: 1, desconocido: 1 });
    expect(resumen.ninos).toBe(5);
  });

  it("cuenta la abstención aparte y no como riesgo bajo", () => {
    const resumen = resumirConjunto([ficha({ riesgo: null })]);
    expect(resumen.porBanda.desconocido).toBe(1);
    expect(resumen.porBanda.bajo).toBe(0);
  });

  it("con la cartera vacía cuenta cero en todas las bandas", () => {
    // `ninos` es el denominador de las barras del widget: si volviera algo
    // distinto de 0 con la cartera vacía, la pantalla dividiría por él.
    const resumen = resumirConjunto([]);
    expect(resumen.ninos).toBe(0);
    expect(resumen.porBanda).toEqual({ alto: 0, medio: 0, bajo: 0, desconocido: 0 });
  });
});
