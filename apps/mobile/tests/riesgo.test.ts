import { describe, expect, it } from "vitest";

import {
  BANDAS_RIESGO,
  CLASE_BANDA,
  CORTE_ALTO,
  CORTE_MEDIO,
  RIESGO_DE_PRUEBA,
  bandaRiesgo,
  bandaSiguiente,
} from "@/theme/riesgo";

describe("bandaRiesgo", () => {
  it("reparte el rango en las tres bandas del diseño", () => {
    expect(bandaRiesgo(0)).toBe("bajo");
    expect(bandaRiesgo(CORTE_MEDIO - 1)).toBe("bajo");
    expect(bandaRiesgo(CORTE_MEDIO)).toBe("medio");
    expect(bandaRiesgo(CORTE_ALTO)).toBe("medio");
    expect(bandaRiesgo(CORTE_ALTO + 1)).toBe("alto");
    expect(bandaRiesgo(100)).toBe("alto");
  });

  it("cada banda tiene su clase y un riesgo de prueba que cae en ella", () => {
    for (const banda of BANDAS_RIESGO) {
      expect(CLASE_BANDA[banda]).toBe(`faro-banda--${banda}`);
      expect(bandaRiesgo(RIESGO_DE_PRUEBA[banda])).toBe(banda);
    }
  });
});

describe("bandaSiguiente", () => {
  it("recorre las tres en círculo", () => {
    expect(bandaSiguiente("bajo")).toBe("medio");
    expect(bandaSiguiente("medio")).toBe("alto");
    expect(bandaSiguiente("alto")).toBe("bajo");
  });
});
