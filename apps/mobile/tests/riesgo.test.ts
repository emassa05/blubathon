import { describe, expect, it } from "vitest";

import {
  BANDA_DE_LA_API,
  BANDAS_RIESGO,
  CLASE_BANDA,
  CORTE_ALTO,
  CORTE_MEDIO,
  bandaRiesgo,
} from "@/theme/riesgo";

describe("bandaRiesgo", () => {
  it("reparte el rango en las tres bandas con estimación", () => {
    expect(bandaRiesgo(0)).toBe("bajo");
    expect(bandaRiesgo(CORTE_MEDIO - 1)).toBe("bajo");
    expect(bandaRiesgo(CORTE_MEDIO)).toBe("medio");
    expect(bandaRiesgo(CORTE_ALTO - 1)).toBe("medio");
    expect(bandaRiesgo(CORTE_ALTO)).toBe("alto");
    expect(bandaRiesgo(100)).toBe("alto");
  });

  it("sin estimación no cae en 'bajo': cae en 'desconocido'", () => {
    expect(bandaRiesgo(null)).toBe("desconocido");
  });

  it("cada banda tiene su clase", () => {
    for (const banda of BANDAS_RIESGO) {
      expect(CLASE_BANDA[banda]).toBe(`faro-banda--${banda}`);
    }
  });
});

describe("BANDA_DE_LA_API", () => {
  it("traduce las cuatro bandas que declara el backend", () => {
    expect(BANDA_DE_LA_API.low).toBe("bajo");
    expect(BANDA_DE_LA_API.medium).toBe("medio");
    expect(BANDA_DE_LA_API.high).toBe("alto");
    expect(BANDA_DE_LA_API.unknown).toBe("desconocido");
  });

  it("no se contradice con los cortes propios", () => {
    // El backend corta en 0.2 y 0.5; la pantalla, en 20 y 50.
    expect(bandaRiesgo(19)).toBe(BANDA_DE_LA_API.low);
    expect(bandaRiesgo(20)).toBe(BANDA_DE_LA_API.medium);
    expect(bandaRiesgo(50)).toBe(BANDA_DE_LA_API.high);
  });
});
