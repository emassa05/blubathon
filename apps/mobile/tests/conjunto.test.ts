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

/** Una serie de `dias` puntos, para que `adherencia` tenga denominador. */
function serie(dias: number): FichaNino["serie"] {
  return Array.from({ length: dias }, (_, indice) => ({
    fecha: `2026-08-${String(indice + 1).padStart(2, "0")}`,
    riesgo: null,
    banda: null,
    resultado: null,
  }));
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

  it("suma días de toda la cartera en vez de promediar porcentajes", () => {
    // Uno con 18 de 20 días y otro con 1 de 10. Promediar los porcentajes daría
    // 0.55; lo correcto es 19/30, porque quien lleva 20 días pesa más que quien
    // lleva 10.
    const resumen = resumirConjunto([
      ficha({ serie: serie(18), adherencia: 18 / 20 }),
      ficha({ serie: serie(1), adherencia: 1 / 10 }),
    ]);
    expect(resumen.adherencia).toBeCloseTo(19 / 30);
  });

  it("suma los cierres pendientes de toda la cartera", () => {
    const resumen = resumirConjunto([ficha({ pendientes: 3 }), ficha({ pendientes: 2 })]);
    expect(resumen.pendientes).toBe(5);
  });

  it("distingue tener niños de tener registros suyos", () => {
    const resumen = resumirConjunto([ficha({ serie: serie(4), adherencia: 1 }), ficha({})]);
    expect(resumen.ninos).toBe(2);
    expect(resumen.conRegistro).toBe(1);
  });

  it("con la cartera vacía no divide por cero", () => {
    const resumen = resumirConjunto([]);
    expect(resumen.ninos).toBe(0);
    expect(resumen.adherencia).toBe(0);
  });
});
